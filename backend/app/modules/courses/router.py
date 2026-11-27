"""Endpoints para catálogo público de estudio libre y autoría de cursos institucionales."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_optional_user, get_tenant_context, require_permission
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationDomainError
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.challenges.models import Challenge
from app.modules.courses.models import Course, Lesson, LessonVersion, Module
from app.modules.courses.schemas import (
    CourseCreate,
    CourseDetailOut,
    CourseSummaryOut,
    LessonCreate,
    LessonOut,
    LessonVersionCreate,
    LessonVersionOut,
    ModuleCreate,
    ModuleOut,
)
from app.modules.tenants.models import OrganizationMember

router = APIRouter(tags=["courses"])


def _build_course_detail(db: Session, course: Course) -> CourseDetailOut:
    modules = db.scalars(
        select(Module)
        .where(Module.course_id == course.id, Module.deleted_at.is_(None))
        .order_by(Module.order_index)
    ).all()

    modules_out: list[ModuleOut] = []
    for mod in modules:
        lessons = db.scalars(
            select(Lesson)
            .where(Lesson.module_id == mod.id, Lesson.deleted_at.is_(None))
            .order_by(Lesson.order_index)
        ).all()
        lessons_out: list[LessonOut] = []
        for les in lessons:
            published_ver = db.scalar(
                select(LessonVersion)
                .where(LessonVersion.lesson_id == les.id, LessonVersion.status == "published")
                .order_by(LessonVersion.version_number.desc())
            )
            lessons_out.append(
                LessonOut(
                    id=les.id,
                    title=les.title,
                    slug=les.slug,
                    order_index=les.order_index,
                    estimated_minutes=les.estimated_minutes,
                    is_safety_critical=les.is_safety_critical,
                    active_lesson_version_id=published_ver.id if published_ver else None,
                    active_version_number=published_ver.version_number if published_ver else None,
                )
            )
        modules_out.append(
            ModuleOut(
                id=mod.id,
                title=mod.title,
                description=mod.description,
                order_index=mod.order_index,
                lessons=lessons_out,
            )
        )

    return CourseDetailOut(
        id=course.id,
        organization_id=course.organization_id,
        title=course.title,
        slug=course.slug,
        description=course.description,
        education_level=course.education_level,
        ui_profile=course.ui_profile,
        visibility=course.visibility,
        status=course.status,
        modules=modules_out,
    )


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
    return [
        CourseSummaryOut(
            id=c.id,
            organization_id=c.organization_id,
            title=c.title,
            slug=c.slug,
            description=c.description,
            education_level=c.education_level,
            ui_profile=c.ui_profile,
            visibility=c.visibility,
            status=c.status,
        )
        for c in courses
    ]


@router.get("/courses/{course_id}", response_model=CourseDetailOut)
def get_course_detail(
    course_id: uuid.UUID,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> CourseDetailOut:
    """Obtiene detalle de curso público o institucional validando tenencia en backend."""
    course = db.scalar(
        select(Course).where(Course.id == course_id, Course.deleted_at.is_(None))
    )
    if not course:
        raise NotFoundError("Curso no encontrado")

    if course.visibility == "public" and course.status == "published":
        return _build_course_detail(db, course)

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

    return _build_course_detail(db, course)


@router.get("/orgs/{org_id}/courses", response_model=list[CourseSummaryOut])
def list_org_courses(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> list[CourseSummaryOut]:
    courses = db.scalars(
        select(Course)
        .where(Course.organization_id == tenant.organization.id, Course.deleted_at.is_(None))
        .order_by(Course.created_at.desc())
    ).all()
    return [
        CourseSummaryOut(
            id=c.id,
            organization_id=c.organization_id,
            title=c.title,
            slug=c.slug,
            description=c.description,
            education_level=c.education_level,
            ui_profile=c.ui_profile,
            visibility=c.visibility,
            status=c.status,
        )
        for c in courses
    ]


@router.post("/orgs/{org_id}/courses", response_model=CourseSummaryOut, status_code=status.HTTP_201_CREATED)
def create_org_course(
    payload: CourseCreate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> CourseSummaryOut:
    dup = db.scalar(
        select(Course).where(
            Course.organization_id == tenant.organization.id,
            func.lower(Course.slug) == payload.slug.lower(),
            Course.deleted_at.is_(None),
        )
    )
    if dup:
        raise ConflictError("Ya existe un curso con ese slug en la organización")

    course = Course(
        organization_id=tenant.organization.id,
        title=payload.title.strip(),
        slug=payload.slug.lower(),
        description=payload.description,
        education_level=payload.education_level,
        ui_profile=payload.ui_profile,
        visibility=payload.visibility,
        status="draft",
        created_by=tenant.user.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return CourseSummaryOut(
        id=course.id,
        organization_id=course.organization_id,
        title=course.title,
        slug=course.slug,
        description=course.description,
        education_level=course.education_level,
        ui_profile=course.ui_profile,
        visibility=course.visibility,
        status=course.status,
    )


@router.post("/orgs/{org_id}/courses/{course_id}/modules", response_model=ModuleOut, status_code=status.HTTP_201_CREATED)
def create_module(
    course_id: uuid.UUID,
    payload: ModuleCreate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> ModuleOut:
    course = db.scalar(
        select(Course).where(
            Course.id == course_id,
            Course.organization_id == tenant.organization.id,
            Course.deleted_at.is_(None),
        )
    )
    if not course:
        raise NotFoundError("Curso no encontrado en esta organización")

    mod = Module(
        course_id=course.id,
        title=payload.title.strip(),
        description=payload.description,
        order_index=payload.order_index,
    )
    db.add(mod)
    db.commit()
    db.refresh(mod)
    return ModuleOut(
        id=mod.id,
        title=mod.title,
        description=mod.description,
        order_index=mod.order_index,
        lessons=[],
    )


@router.post("/orgs/{org_id}/modules/{module_id}/lessons", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
def create_lesson(
    module_id: uuid.UUID,
    payload: LessonCreate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> LessonOut:
    mod_course = db.execute(
        select(Module, Course)
        .join(Course, Module.course_id == Course.id)
        .where(
            Module.id == module_id,
            Module.deleted_at.is_(None),
            Course.organization_id == tenant.organization.id,
            Course.deleted_at.is_(None),
        )
    ).first()
    if not mod_course:
        raise NotFoundError("Módulo no encontrado en esta organización")

    lesson = Lesson(
        module_id=module_id,
        title=payload.title.strip(),
        slug=payload.slug.lower(),
        order_index=payload.order_index,
        estimated_minutes=payload.estimated_minutes,
        is_safety_critical=payload.is_safety_critical,
    )
    db.add(lesson)
    db.flush()

    v1 = LessonVersion(
        lesson_id=lesson.id,
        version_number=1,
        summary="Versión inicial",
        status="draft",
    )
    db.add(v1)
    db.commit()
    db.refresh(lesson)
    return LessonOut(
        id=lesson.id,
        title=lesson.title,
        slug=lesson.slug,
        order_index=lesson.order_index,
        estimated_minutes=lesson.estimated_minutes,
        is_safety_critical=lesson.is_safety_critical,
        active_lesson_version_id=v1.id,
        active_version_number=v1.version_number,
    )


@router.get("/orgs/{org_id}/lessons/{lesson_id}/versions", response_model=list[LessonVersionOut])
def list_lesson_versions(
    lesson_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> list[LessonVersionOut]:
    row = db.execute(
        select(Lesson, Course)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            Lesson.id == lesson_id,
            Lesson.deleted_at.is_(None),
            Course.organization_id == tenant.organization.id,
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Lección no encontrada en esta organización")

    versions = db.scalars(
        select(LessonVersion)
        .where(LessonVersion.lesson_id == lesson_id)
        .order_by(LessonVersion.version_number.desc())
    ).all()
    return [
        LessonVersionOut(
            id=lv.id,
            lesson_id=lv.lesson_id,
            version_number=lv.version_number,
            summary=lv.summary,
            status=lv.status,
            requires_revalidation=lv.requires_revalidation,
            published_at=lv.published_at,
        )
        for lv in versions
    ]


@router.post("/orgs/{org_id}/lessons/{lesson_id}/versions", response_model=LessonVersionOut, status_code=status.HTTP_201_CREATED)
def create_lesson_version(
    lesson_id: uuid.UUID,
    payload: LessonVersionCreate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> LessonVersionOut:
    row = db.execute(
        select(Lesson, Course)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            Lesson.id == lesson_id,
            Lesson.deleted_at.is_(None),
            Course.organization_id == tenant.organization.id,
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Lección no encontrada en esta organización")

    max_ver = db.scalar(
        select(func.coalesce(func.max(LessonVersion.version_number), 0)).where(
            LessonVersion.lesson_id == lesson_id
        )
    )
    lv = LessonVersion(
        lesson_id=lesson_id,
        version_number=int(max_ver or 0) + 1,
        summary=payload.summary,
        requires_revalidation=payload.requires_revalidation,
        status="draft",
    )
    db.add(lv)
    db.commit()
    db.refresh(lv)
    return LessonVersionOut(
        id=lv.id,
        lesson_id=lv.lesson_id,
        version_number=lv.version_number,
        summary=lv.summary,
        status=lv.status,
        requires_revalidation=lv.requires_revalidation,
        published_at=lv.published_at,
    )


@router.post("/orgs/{org_id}/lesson-versions/{lesson_version_id}/publish", response_model=LessonVersionOut)
def publish_lesson_version(
    lesson_version_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> LessonVersionOut:
    row = db.execute(
        select(LessonVersion, Lesson, Course)
        .join(Lesson, LessonVersion.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            LessonVersion.id == lesson_version_id,
            Course.organization_id == tenant.organization.id,
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Versión de lección no encontrada en esta organización")

    lv, lesson, course = row
    challenges = db.scalars(
        select(Challenge).where(Challenge.lesson_version_id == lv.id, Challenge.deleted_at.is_(None))
    ).all()
    if not challenges:
        raise ValidationDomainError("La versión de lección debe tener al menos un reto antes de publicarse")

    # Marca versiones publicadas anteriores como superseded sin tocar el progreso histórico
    prev_published = db.scalars(
        select(LessonVersion).where(
            LessonVersion.lesson_id == lesson.id,
            LessonVersion.status == "published",
            LessonVersion.id != lv.id,
        )
    ).all()
    for prev in prev_published:
        prev.status = "superseded"

    for ch in challenges:
        if ch.status == "draft":
            ch.status = "published"

    lv.status = "published"
    lv.published_by = tenant.user.id
    lv.published_at = datetime.now(timezone.utc)
    if course.status == "draft":
        course.status = "published"

    db.commit()
    db.refresh(lv)
    return LessonVersionOut(
        id=lv.id,
        lesson_id=lv.lesson_id,
        version_number=lv.version_number,
        summary=lv.summary,
        status=lv.status,
        requires_revalidation=lv.requires_revalidation,
        published_at=lv.published_at,
    )
