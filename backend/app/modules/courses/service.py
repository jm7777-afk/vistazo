"""Servicios compartidos para autoría CRUD de cursos, módulos, lecciones y guías de estudio."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationDomainError
from app.modules.challenges.models import Challenge
from app.modules.courses.models import Course, Lesson, LessonVersion, Module, StudyGuide
from app.modules.courses.schemas import (
    CourseCreate,
    CourseDetailOut,
    CourseSummaryOut,
    CourseUpdate,
    LessonCreate,
    LessonOut,
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


def to_course_summary(course: Course) -> CourseSummaryOut:
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


def build_course_detail(db: Session, course: Course) -> CourseDetailOut:
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
            latest_ver = published_ver or db.scalar(
                select(LessonVersion)
                .where(LessonVersion.lesson_id == les.id)
                .order_by(LessonVersion.version_number.desc())
            )
            lessons_out.append(
                LessonOut(
                    id=les.id,
                    title=les.title,
                    slug=les.slug,
                    order_index=les.order_index,
                    estimated_minutes=les.estimated_minutes,
                    lesson_type=les.lesson_type,
                    passing_score_pct=les.passing_score_pct,
                    is_safety_critical=les.is_safety_critical,
                    active_lesson_version_id=latest_ver.id if latest_ver else None,
                    active_version_number=latest_ver.version_number if latest_ver else None,
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
        **to_course_summary(course).model_dump(),
        modules=modules_out,
    )


def _scope_filter(model_org_col, organization_id: uuid.UUID | None):
    if organization_id is None:
        return model_org_col.is_(None)
    return model_org_col == organization_id


def get_scoped_course(db: Session, course_id: uuid.UUID, organization_id: uuid.UUID | None) -> Course:
    course = db.scalar(
        select(Course).where(
            Course.id == course_id,
            _scope_filter(Course.organization_id, organization_id),
            Course.deleted_at.is_(None),
        )
    )
    if not course:
        raise NotFoundError("Curso no encontrado en este ámbito")
    return course


def list_scoped_courses(db: Session, organization_id: uuid.UUID | None) -> list[CourseSummaryOut]:
    courses = db.scalars(
        select(Course)
        .where(_scope_filter(Course.organization_id, organization_id), Course.deleted_at.is_(None))
        .order_by(Course.created_at.desc())
    ).all()
    return [to_course_summary(c) for c in courses]


def create_scoped_course(
    db: Session,
    *,
    organization_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
    payload: CourseCreate,
) -> CourseSummaryOut:
    dup = db.scalar(
        select(Course).where(
            _scope_filter(Course.organization_id, organization_id),
            func.lower(Course.slug) == payload.slug.lower(),
            Course.deleted_at.is_(None),
        )
    )
    if dup:
        raise ConflictError("Ya existe un curso con ese slug en este ámbito")

    visibility = "public" if organization_id is None else (
        "institutional" if payload.visibility == "public" else payload.visibility
    )
    course = Course(
        organization_id=organization_id,
        title=payload.title.strip(),
        slug=payload.slug.lower(),
        description=payload.description,
        education_level=payload.education_level,
        ui_profile=payload.ui_profile,
        visibility=visibility,
        status="draft",
        created_by=actor_user_id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return to_course_summary(course)


def update_scoped_course(
    db: Session,
    *,
    course_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    payload: CourseUpdate,
) -> CourseSummaryOut:
    course = get_scoped_course(db, course_id, organization_id)
    if payload.title is not None:
        course.title = payload.title.strip()
    if payload.description is not None:
        course.description = payload.description
    if payload.education_level is not None:
        course.education_level = payload.education_level
    if payload.ui_profile is not None:
        course.ui_profile = payload.ui_profile
    if payload.visibility is not None:
        if organization_id is None and payload.visibility != "public":
            raise ValidationDomainError("Los cursos globales del catálogo deben tener visibilidad public")
        if organization_id is not None and payload.visibility == "public":
            raise ValidationDomainError("Los cursos organizacionales deben usar visibilidad institutional o private")
        course.visibility = payload.visibility
    if payload.status is not None:
        course.status = payload.status
    db.commit()
    db.refresh(course)
    return to_course_summary(course)


def delete_scoped_course(
    db: Session,
    *,
    course_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
) -> None:
    course = get_scoped_course(db, course_id, organization_id)
    course.deleted_at = datetime.now(timezone.utc)
    course.deleted_by = actor_user_id
    db.commit()


def create_scoped_module(
    db: Session,
    *,
    course_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    payload: ModuleCreate,
) -> ModuleOut:
    course = get_scoped_course(db, course_id, organization_id)
    mod = Module(
        course_id=course.id,
        title=payload.title.strip(),
        description=payload.description,
        order_index=payload.order_index,
    )
    db.add(mod)
    db.commit()
    db.refresh(mod)
    return ModuleOut(id=mod.id, title=mod.title, description=mod.description, order_index=mod.order_index, lessons=[])


def update_scoped_module(
    db: Session,
    *,
    module_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    payload: ModuleUpdate,
) -> ModuleOut:
    row = db.execute(
        select(Module, Course)
        .join(Course, Module.course_id == Course.id)
        .where(
            Module.id == module_id,
            Module.deleted_at.is_(None),
            _scope_filter(Course.organization_id, organization_id),
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Módulo no encontrado")
    mod, _course = row
    if payload.title is not None:
        mod.title = payload.title.strip()
    if payload.description is not None:
        mod.description = payload.description
    if payload.order_index is not None:
        mod.order_index = payload.order_index
    db.commit()
    db.refresh(mod)
    return ModuleOut(id=mod.id, title=mod.title, description=mod.description, order_index=mod.order_index, lessons=[])


def delete_scoped_module(db: Session, *, module_id: uuid.UUID, organization_id: uuid.UUID | None) -> None:
    row = db.execute(
        select(Module, Course)
        .join(Course, Module.course_id == Course.id)
        .where(
            Module.id == module_id,
            Module.deleted_at.is_(None),
            _scope_filter(Course.organization_id, organization_id),
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Módulo no encontrado")
    mod, _course = row
    mod.deleted_at = datetime.now(timezone.utc)
    db.commit()


def create_scoped_lesson(
    db: Session,
    *,
    module_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    payload: LessonCreate,
) -> LessonOut:
    row = db.execute(
        select(Module, Course)
        .join(Course, Module.course_id == Course.id)
        .where(
            Module.id == module_id,
            Module.deleted_at.is_(None),
            _scope_filter(Course.organization_id, organization_id),
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Módulo no encontrado en este ámbito")

    lesson = Lesson(
        module_id=module_id,
        title=payload.title.strip(),
        slug=payload.slug.lower(),
        order_index=payload.order_index,
        estimated_minutes=payload.estimated_minutes,
        lesson_type=payload.lesson_type,
        passing_score_pct=payload.passing_score_pct,
        is_safety_critical=payload.is_safety_critical,
    )
    db.add(lesson)
    db.flush()
    v1 = LessonVersion(lesson_id=lesson.id, version_number=1, summary="Versión inicial", status="draft")
    db.add(v1)
    db.commit()
    db.refresh(lesson)
    return LessonOut(
        id=lesson.id,
        title=lesson.title,
        slug=lesson.slug,
        order_index=lesson.order_index,
        estimated_minutes=lesson.estimated_minutes,
        lesson_type=lesson.lesson_type,
        passing_score_pct=lesson.passing_score_pct,
        is_safety_critical=lesson.is_safety_critical,
        active_lesson_version_id=v1.id,
        active_version_number=v1.version_number,
    )


def update_scoped_lesson(
    db: Session,
    *,
    lesson_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    payload: LessonUpdate,
) -> LessonOut:
    row = db.execute(
        select(Lesson, Course)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            Lesson.id == lesson_id,
            Lesson.deleted_at.is_(None),
            _scope_filter(Course.organization_id, organization_id),
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Lección no encontrada")
    lesson, _course = row
    if payload.title is not None:
        lesson.title = payload.title.strip()
    if payload.order_index is not None:
        lesson.order_index = payload.order_index
    if payload.estimated_minutes is not None:
        lesson.estimated_minutes = payload.estimated_minutes
    if payload.lesson_type is not None:
        lesson.lesson_type = payload.lesson_type
    if payload.passing_score_pct is not None:
        lesson.passing_score_pct = payload.passing_score_pct
    if payload.is_safety_critical is not None:
        lesson.is_safety_critical = payload.is_safety_critical
    db.commit()
    db.refresh(lesson)
    latest_ver = db.scalar(
        select(LessonVersion).where(LessonVersion.lesson_id == lesson.id).order_by(LessonVersion.version_number.desc())
    )
    return LessonOut(
        id=lesson.id,
        title=lesson.title,
        slug=lesson.slug,
        order_index=lesson.order_index,
        estimated_minutes=lesson.estimated_minutes,
        lesson_type=lesson.lesson_type,
        passing_score_pct=lesson.passing_score_pct,
        is_safety_critical=lesson.is_safety_critical,
        active_lesson_version_id=latest_ver.id if latest_ver else None,
        active_version_number=latest_ver.version_number if latest_ver else None,
    )


def delete_scoped_lesson(db: Session, *, lesson_id: uuid.UUID, organization_id: uuid.UUID | None) -> None:
    row = db.execute(
        select(Lesson, Course)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            Lesson.id == lesson_id,
            Lesson.deleted_at.is_(None),
            _scope_filter(Course.organization_id, organization_id),
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Lección no encontrada")
    lesson, _course = row
    lesson.deleted_at = datetime.now(timezone.utc)
    db.commit()


def list_scoped_lesson_versions(
    db: Session, *, lesson_id: uuid.UUID, organization_id: uuid.UUID | None
) -> list[LessonVersionOut]:
    row = db.execute(
        select(Lesson, Course)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            Lesson.id == lesson_id,
            Lesson.deleted_at.is_(None),
            _scope_filter(Course.organization_id, organization_id),
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Lección no encontrada en este ámbito")

    versions = db.scalars(
        select(LessonVersion).where(LessonVersion.lesson_id == lesson_id).order_by(LessonVersion.version_number.desc())
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


def create_scoped_lesson_version(
    db: Session,
    *,
    lesson_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    payload: LessonVersionCreate,
) -> LessonVersionOut:
    row = db.execute(
        select(Lesson, Course)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            Lesson.id == lesson_id,
            Lesson.deleted_at.is_(None),
            _scope_filter(Course.organization_id, organization_id),
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Lección no encontrada en este ámbito")

    max_ver = db.scalar(
        select(func.coalesce(func.max(LessonVersion.version_number), 0)).where(LessonVersion.lesson_id == lesson_id)
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


def publish_scoped_lesson_version(
    db: Session,
    *,
    lesson_version_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
) -> LessonVersionOut:
    row = db.execute(
        select(LessonVersion, Lesson, Course)
        .join(Lesson, LessonVersion.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            LessonVersion.id == lesson_version_id,
            _scope_filter(Course.organization_id, organization_id),
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Versión de lección no encontrada en este ámbito")

    lv, lesson, course = row
    challenges = db.scalars(
        select(Challenge).where(Challenge.lesson_version_id == lv.id, Challenge.deleted_at.is_(None))
    ).all()
    if not challenges:
        raise ValidationDomainError("La versión de lección debe tener al menos un reto antes de publicarse")

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
    lv.published_by = actor_user_id
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


def _to_guide_out(g: StudyGuide) -> StudyGuideOut:
    return StudyGuideOut(
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


def list_scoped_study_guides(
    db: Session,
    *,
    organization_id: uuid.UUID | None,
    course_id: uuid.UUID | None = None,
) -> list[StudyGuideOut]:
    stmt = select(StudyGuide).where(
        _scope_filter(StudyGuide.organization_id, organization_id),
        StudyGuide.deleted_at.is_(None),
    )
    if course_id is not None:
        stmt = stmt.where(StudyGuide.course_id == course_id)
    rows = db.scalars(stmt.order_by(StudyGuide.updated_at.desc())).all()
    return [_to_guide_out(r) for r in rows]


def create_scoped_study_guide(
    db: Session,
    *,
    organization_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
    payload: StudyGuideCreate,
    ai_generated: bool = False,
) -> StudyGuideOut:
    if payload.course_id is not None:
        get_scoped_course(db, payload.course_id, organization_id)
    guide = StudyGuide(
        organization_id=organization_id,
        course_id=payload.course_id,
        lesson_id=payload.lesson_id,
        guide_type=payload.guide_type,
        title=payload.title.strip(),
        content_markdown=payload.content_markdown.strip(),
        methodology_json=payload.methodology_json,
        status=payload.status,
        ai_generated=ai_generated,
        created_by=actor_user_id,
    )
    db.add(guide)
    db.commit()
    db.refresh(guide)
    return _to_guide_out(guide)


def update_scoped_study_guide(
    db: Session,
    *,
    guide_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    payload: StudyGuideUpdate,
) -> StudyGuideOut:
    guide = db.scalar(
        select(StudyGuide).where(
            StudyGuide.id == guide_id,
            _scope_filter(StudyGuide.organization_id, organization_id),
            StudyGuide.deleted_at.is_(None),
        )
    )
    if not guide:
        raise NotFoundError("Guía de estudio no encontrada")
    if payload.guide_type is not None:
        guide.guide_type = payload.guide_type
    if payload.title is not None:
        guide.title = payload.title.strip()
    if payload.content_markdown is not None:
        guide.content_markdown = payload.content_markdown.strip()
    if payload.methodology_json is not None:
        guide.methodology_json = payload.methodology_json
    if payload.status is not None:
        guide.status = payload.status
    db.commit()
    db.refresh(guide)
    return _to_guide_out(guide)


def delete_scoped_study_guide(
    db: Session,
    *,
    guide_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
) -> None:
    guide = db.scalar(
        select(StudyGuide).where(
            StudyGuide.id == guide_id,
            _scope_filter(StudyGuide.organization_id, organization_id),
            StudyGuide.deleted_at.is_(None),
        )
    )
    if not guide:
        raise NotFoundError("Guía de estudio no encontrada")
    guide.deleted_at = datetime.now(timezone.utc)
    guide.deleted_by = actor_user_id
    db.commit()
