"""Endpoints para catálogo público, cursos, módulos, lecciones y guías de estudio (Org + SuperAdmin)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_optional_user, get_tenant_context, require_permission, require_super_admin
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.challenges.models import Challenge
from app.modules.courses.models import Course, Lesson, LessonVersion, Module, StudyGuide
from app.modules.courses.pdf_export import render_lesson_exam_pdf, render_study_guide_pdf
from app.modules.courses.schemas import (
    CourseCreate,
    CourseDetailOut,
    CourseSummaryOut,
    CourseUpdate,
    LessonCreate,
    LessonOut,
    LessonPlayerContextOut,
    LessonUpdate,
    LessonVersionCreate,
    LessonVersionOut,
    ModuleCreate,
    ModuleOut,
    ModuleUpdate,
    StudyGuideCreate,
    StudyGuideOut,
    StudyGuideUpdate,
)
from app.modules.courses.service import (
    build_course_detail,
    create_scoped_course,
    create_scoped_lesson,
    create_scoped_lesson_version,
    create_scoped_module,
    create_scoped_study_guide,
    delete_scoped_course,
    delete_scoped_lesson,
    delete_scoped_module,
    delete_scoped_study_guide,
    list_scoped_courses,
    list_scoped_lesson_versions,
    list_scoped_study_guides,
    publish_scoped_lesson_version,
    to_course_summary,
    update_scoped_course,
    update_scoped_lesson,
    update_scoped_module,
    update_scoped_study_guide,
)
from app.modules.tenants.models import OrganizationMember

router = APIRouter(tags=["courses"])


# ---------------------------------------------------------------------------
# Lectura pública / estudiante
# ---------------------------------------------------------------------------
@router.get("/catalog/courses", response_model=list[CourseSummaryOut])
def list_public_catalog(db: Session = Depends(get_db)) -> list[CourseSummaryOut]:
    """Catálogo de cursos públicos para Modo Estudio Libre."""
    courses = db.scalars(
        select(Course)
        .where(
            Course.visibility == "public",
            Course.status == "published",
            Course.organization_id.is_(None),
            Course.deleted_at.is_(None),
        )
        .order_by(Course.created_at.desc())
    ).all()
    return [to_course_summary(c) for c in courses]


@router.get("/courses/{course_id}", response_model=CourseDetailOut)
def get_course_detail(
    course_id: uuid.UUID,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> CourseDetailOut:
    """Obtiene detalle de curso público o institucional validando tenencia en backend."""
    course = db.scalar(select(Course).where(Course.id == course_id, Course.deleted_at.is_(None)))
    if not course:
        raise NotFoundError("Curso no encontrado")

    if course.visibility == "public" and course.status == "published":
        return build_course_detail(db, course)

    if not current_user:
        raise ForbiddenError("Acceso restringido a miembros de la organización")

    if not current_user.is_super_admin:
        member = db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == course.organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.deleted_at.is_(None),
                OrganizationMember.status == "active",
            )
        )
        if not member:
            raise ForbiddenError("No tienes acceso a cursos de esta organización")

    return build_course_detail(db, course)


@router.get("/courses/{course_id}/study-guides", response_model=list[StudyGuideOut])
def list_course_published_guides(
    course_id: uuid.UUID,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> list[StudyGuideOut]:
    """Devuelve guías de estudio, temarios y metodologías publicadas del curso."""
    course = db.scalar(select(Course).where(Course.id == course_id, Course.deleted_at.is_(None)))
    if not course:
        raise NotFoundError("Curso no encontrado")

    if not (course.visibility == "public" and course.status == "published"):
        if not current_user:
            raise ForbiddenError("Acceso restringido")
        if not current_user.is_super_admin:
            member = db.scalar(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == course.organization_id,
                    OrganizationMember.user_id == current_user.id,
                    OrganizationMember.deleted_at.is_(None),
                    OrganizationMember.status == "active",
                )
            )
            if not member:
                raise ForbiddenError("No tienes acceso a este curso")

    guides = db.scalars(
        select(StudyGuide)
        .where(
            StudyGuide.course_id == course.id,
            StudyGuide.status == "published",
            StudyGuide.deleted_at.is_(None),
        )
        .order_by(StudyGuide.created_at.asc())
    ).all()
    return [
        StudyGuideOut(
            id=g.id,
            organization_id=g.organization_id,
            course_id=g.course_id,
            lesson_id=g.lesson_id,
            guide_type=g.guide_type,
            title=g.title,
            content_markdown=g.content_markdown,
            methodology_json=g.methodology_json,
            status=g.status,
            ai_generated=g.ai_generated,
            created_at=g.created_at,
            updated_at=g.updated_at,
        )
        for g in guides
    ]


# ---------------------------------------------------------------------------
# CRUD Institucional (Educador / Coordinador / Instructor / SuperAdmin en org)
# ---------------------------------------------------------------------------
@router.get("/orgs/{org_id}/courses", response_model=list[CourseSummaryOut])
def list_org_courses(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> list[CourseSummaryOut]:
    return list_scoped_courses(db, tenant.organization.id)


@router.post("/orgs/{org_id}/courses", response_model=CourseSummaryOut, status_code=status.HTTP_201_CREATED)
def create_org_course(
    payload: CourseCreate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> CourseSummaryOut:
    return create_scoped_course(
        db, organization_id=tenant.organization.id, actor_user_id=tenant.user.id, payload=payload
    )


@router.patch("/orgs/{org_id}/courses/{course_id}", response_model=CourseSummaryOut)
def update_org_course(
    course_id: uuid.UUID,
    payload: CourseUpdate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> CourseSummaryOut:
    return update_scoped_course(
        db, course_id=course_id, organization_id=tenant.organization.id, payload=payload
    )


@router.delete("/orgs/{org_id}/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_org_course(
    course_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> Response:
    delete_scoped_course(
        db, course_id=course_id, organization_id=tenant.organization.id, actor_user_id=tenant.user.id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/orgs/{org_id}/courses/{course_id}/modules", response_model=ModuleOut, status_code=status.HTTP_201_CREATED)
def create_org_module(
    course_id: uuid.UUID,
    payload: ModuleCreate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> ModuleOut:
    return create_scoped_module(
        db, course_id=course_id, organization_id=tenant.organization.id, payload=payload
    )


@router.patch("/orgs/{org_id}/modules/{module_id}", response_model=ModuleOut)
def update_org_module(
    module_id: uuid.UUID,
    payload: ModuleUpdate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> ModuleOut:
    return update_scoped_module(
        db, module_id=module_id, organization_id=tenant.organization.id, payload=payload
    )


@router.delete("/orgs/{org_id}/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_org_module(
    module_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> Response:
    delete_scoped_module(db, module_id=module_id, organization_id=tenant.organization.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/orgs/{org_id}/modules/{module_id}/lessons", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
def create_org_lesson(
    module_id: uuid.UUID,
    payload: LessonCreate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> LessonOut:
    return create_scoped_lesson(
        db, module_id=module_id, organization_id=tenant.organization.id, payload=payload
    )


@router.patch("/orgs/{org_id}/lessons/{lesson_id}", response_model=LessonOut)
def update_org_lesson(
    lesson_id: uuid.UUID,
    payload: LessonUpdate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> LessonOut:
    return update_scoped_lesson(
        db, lesson_id=lesson_id, organization_id=tenant.organization.id, payload=payload
    )


@router.delete("/orgs/{org_id}/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_org_lesson(
    lesson_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> Response:
    delete_scoped_lesson(db, lesson_id=lesson_id, organization_id=tenant.organization.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/orgs/{org_id}/lessons/{lesson_id}/versions", response_model=list[LessonVersionOut])
def list_org_lesson_versions(
    lesson_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> list[LessonVersionOut]:
    return list_scoped_lesson_versions(db, lesson_id=lesson_id, organization_id=tenant.organization.id)


@router.post("/orgs/{org_id}/lessons/{lesson_id}/versions", response_model=LessonVersionOut, status_code=status.HTTP_201_CREATED)
def create_org_lesson_version(
    lesson_id: uuid.UUID,
    payload: LessonVersionCreate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> LessonVersionOut:
    return create_scoped_lesson_version(
        db, lesson_id=lesson_id, organization_id=tenant.organization.id, payload=payload
    )


@router.post("/orgs/{org_id}/lesson-versions/{lesson_version_id}/publish", response_model=LessonVersionOut)
def publish_org_lesson_version(
    lesson_version_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> LessonVersionOut:
    return publish_scoped_lesson_version(
        db,
        lesson_version_id=lesson_version_id,
        organization_id=tenant.organization.id,
        actor_user_id=tenant.user.id,
    )


@router.get("/orgs/{org_id}/study-guides", response_model=list[StudyGuideOut])
def list_org_study_guides(
    course_id: uuid.UUID | None = Query(default=None),
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> list[StudyGuideOut]:
    return list_scoped_study_guides(db, organization_id=tenant.organization.id, course_id=course_id)


@router.post("/orgs/{org_id}/study-guides", response_model=StudyGuideOut, status_code=status.HTTP_201_CREATED)
def create_org_study_guide(
    payload: StudyGuideCreate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> StudyGuideOut:
    return create_scoped_study_guide(
        db, organization_id=tenant.organization.id, actor_user_id=tenant.user.id, payload=payload
    )


@router.patch("/orgs/{org_id}/study-guides/{guide_id}", response_model=StudyGuideOut)
def update_org_study_guide(
    guide_id: uuid.UUID,
    payload: StudyGuideUpdate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> StudyGuideOut:
    return update_scoped_study_guide(
        db, guide_id=guide_id, organization_id=tenant.organization.id, payload=payload
    )


@router.delete("/orgs/{org_id}/study-guides/{guide_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_org_study_guide(
    guide_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> Response:
    delete_scoped_study_guide(
        db, guide_id=guide_id, organization_id=tenant.organization.id, actor_user_id=tenant.user.id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# CRUD Global SuperAdmin (Catálogo Libre Público: organization_id IS NULL)
# ---------------------------------------------------------------------------
@router.get("/admin/courses", response_model=list[CourseSummaryOut])
def list_global_courses(
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[CourseSummaryOut]:
    return list_scoped_courses(db, None)


@router.post("/admin/courses", response_model=CourseSummaryOut, status_code=status.HTTP_201_CREATED)
def create_global_course(
    payload: CourseCreate,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> CourseSummaryOut:
    return create_scoped_course(db, organization_id=None, actor_user_id=admin.id, payload=payload)


@router.patch("/admin/courses/{course_id}", response_model=CourseSummaryOut)
def update_global_course(
    course_id: uuid.UUID,
    payload: CourseUpdate,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> CourseSummaryOut:
    return update_scoped_course(db, course_id=course_id, organization_id=None, payload=payload)


@router.delete("/admin/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_global_course(
    course_id: uuid.UUID,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Response:
    delete_scoped_course(db, course_id=course_id, organization_id=None, actor_user_id=admin.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/admin/courses/{course_id}/modules", response_model=ModuleOut, status_code=status.HTTP_201_CREATED)
def create_global_module(
    course_id: uuid.UUID,
    payload: ModuleCreate,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ModuleOut:
    return create_scoped_module(db, course_id=course_id, organization_id=None, payload=payload)


@router.patch("/admin/modules/{module_id}", response_model=ModuleOut)
def update_global_module(
    module_id: uuid.UUID,
    payload: ModuleUpdate,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ModuleOut:
    return update_scoped_module(db, module_id=module_id, organization_id=None, payload=payload)


@router.delete("/admin/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_global_module(
    module_id: uuid.UUID,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Response:
    delete_scoped_module(db, module_id=module_id, organization_id=None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/admin/modules/{module_id}/lessons", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
def create_global_lesson(
    module_id: uuid.UUID,
    payload: LessonCreate,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> LessonOut:
    return create_scoped_lesson(db, module_id=module_id, organization_id=None, payload=payload)


@router.patch("/admin/lessons/{lesson_id}", response_model=LessonOut)
def update_global_lesson(
    lesson_id: uuid.UUID,
    payload: LessonUpdate,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> LessonOut:
    return update_scoped_lesson(db, lesson_id=lesson_id, organization_id=None, payload=payload)


@router.delete("/admin/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_global_lesson(
    lesson_id: uuid.UUID,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Response:
    delete_scoped_lesson(db, lesson_id=lesson_id, organization_id=None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/admin/lessons/{lesson_id}/versions", response_model=list[LessonVersionOut])
def list_global_lesson_versions(
    lesson_id: uuid.UUID,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[LessonVersionOut]:
    return list_scoped_lesson_versions(db, lesson_id=lesson_id, organization_id=None)


@router.post("/admin/lessons/{lesson_id}/versions", response_model=LessonVersionOut, status_code=status.HTTP_201_CREATED)
def create_global_lesson_version(
    lesson_id: uuid.UUID,
    payload: LessonVersionCreate,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> LessonVersionOut:
    return create_scoped_lesson_version(db, lesson_id=lesson_id, organization_id=None, payload=payload)


@router.post("/admin/lesson-versions/{lesson_version_id}/publish", response_model=LessonVersionOut)
def publish_global_lesson_version(
    lesson_version_id: uuid.UUID,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> LessonVersionOut:
    return publish_scoped_lesson_version(
        db, lesson_version_id=lesson_version_id, organization_id=None, actor_user_id=admin.id
    )


@router.get("/admin/study-guides", response_model=list[StudyGuideOut])
def list_global_study_guides(
    course_id: uuid.UUID | None = Query(default=None),
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[StudyGuideOut]:
    return list_scoped_study_guides(db, organization_id=None, course_id=course_id)


@router.post("/admin/study-guides", response_model=StudyGuideOut, status_code=status.HTTP_201_CREATED)
def create_global_study_guide(
    payload: StudyGuideCreate,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> StudyGuideOut:
    return create_scoped_study_guide(db, organization_id=None, actor_user_id=admin.id, payload=payload)


@router.patch("/admin/study-guides/{guide_id}", response_model=StudyGuideOut)
def update_global_study_guide(
    guide_id: uuid.UUID,
    payload: StudyGuideUpdate,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> StudyGuideOut:
    return update_scoped_study_guide(db, guide_id=guide_id, organization_id=None, payload=payload)


@router.delete("/admin/study-guides/{guide_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_global_study_guide(
    guide_id: uuid.UUID,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Response:
    delete_scoped_study_guide(db, guide_id=guide_id, organization_id=None, actor_user_id=admin.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Contexto de Reproductor + Exportación PDF de Guías y Pruebas Fuertes
# ---------------------------------------------------------------------------
@router.get("/lesson-versions/{lesson_version_id}/context", response_model=LessonPlayerContextOut)
def get_lesson_player_context(
    lesson_version_id: uuid.UUID,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> LessonPlayerContextOut:
    """Devuelve metadatos de tiempo, tipo y nota mínima para el reproductor de lección/examen."""
    row = db.execute(
        select(LessonVersion, Lesson, Course)
        .join(Lesson, LessonVersion.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(LessonVersion.id == lesson_version_id, Course.deleted_at.is_(None))
    ).first()
    if not row:
        raise NotFoundError("Versión de lección no encontrada")
    _lv, lesson, course = row
    if course.visibility != "public":
        if not current_user:
            raise ForbiddenError("Autenticación requerida")
        if not current_user.is_super_admin:
            member = db.scalar(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == course.organization_id,
                    OrganizationMember.user_id == current_user.id,
                    OrganizationMember.deleted_at.is_(None),
                    OrganizationMember.status == "active",
                )
            )
            if not member:
                raise ForbiddenError("Sin acceso al curso")
    return LessonPlayerContextOut(
        lesson_id=lesson.id,
        lesson_title=lesson.title,
        lesson_type=lesson.lesson_type,
        estimated_minutes=lesson.estimated_minutes,
        passing_score_pct=lesson.passing_score_pct,
        is_safety_critical=lesson.is_safety_critical,
        course_id=course.id,
        course_title=course.title,
    )


def _export_guide_pdf_impl(db: Session, guide_id: uuid.UUID, organization_id: uuid.UUID | None) -> Response:
    cond = StudyGuide.organization_id.is_(None) if organization_id is None else (StudyGuide.organization_id == organization_id)
    guide = db.scalar(select(StudyGuide).where(StudyGuide.id == guide_id, cond, StudyGuide.deleted_at.is_(None)))
    if not guide:
        raise NotFoundError("Guía de estudio no encontrada")
    course_title = "Vistazo LMS"
    if guide.course_id:
        course = db.scalar(select(Course).where(Course.id == guide.course_id))
        if course:
            course_title = course.title
    pdf_bytes = render_study_guide_pdf(guide=guide, course_title=course_title)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="guia-{guide.id}.pdf"'},
    )


@router.get("/orgs/{org_id}/study-guides/{guide_id}/pdf")
def export_org_study_guide_pdf(
    guide_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> Response:
    return _export_guide_pdf_impl(db, guide_id, tenant.organization.id)


@router.get("/admin/study-guides/{guide_id}/pdf")
def export_global_study_guide_pdf(
    guide_id: uuid.UUID,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Response:
    return _export_guide_pdf_impl(db, guide_id, None)


def _export_exam_pdf_impl(
    db: Session, lv_id: uuid.UUID, organization_id: uuid.UUID | None, include_answers: bool
) -> Response:
    cond = Course.organization_id.is_(None) if organization_id is None else (Course.organization_id == organization_id)
    row = db.execute(
        select(LessonVersion, Lesson, Course)
        .join(Lesson, LessonVersion.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(LessonVersion.id == lv_id, cond, Course.deleted_at.is_(None))
    ).first()
    if not row:
        raise NotFoundError("Versión de lección no encontrada")
    lv, lesson, course = row
    challenges = db.scalars(
        select(Challenge)
        .where(Challenge.lesson_version_id == lv.id, Challenge.deleted_at.is_(None))
        .order_by(Challenge.order_index)
    ).all()
    pdf_bytes = render_lesson_exam_pdf(
        lesson=lesson,
        lv=lv,
        challenges=list(challenges),
        course_title=course.title,
        include_answers=include_answers,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="evaluacion-{lv.id}.pdf"'},
    )


@router.get("/orgs/{org_id}/lesson-versions/{lesson_version_id}/exam-pdf")
def export_org_exam_pdf(
    lesson_version_id: uuid.UUID,
    include_answers: bool = Query(default=False),
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> Response:
    return _export_exam_pdf_impl(db, lesson_version_id, tenant.organization.id, include_answers)


@router.get("/admin/lesson-versions/{lesson_version_id}/exam-pdf")
def export_global_exam_pdf(
    lesson_version_id: uuid.UUID,
    include_answers: bool = Query(default=False),
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Response:
    return _export_exam_pdf_impl(db, lesson_version_id, None, include_answers)
