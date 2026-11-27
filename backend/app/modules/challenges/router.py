"""Endpoints de autoría CRUD y lectura segura de retos por versión de lección."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_optional_user, require_permission, require_super_admin
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.challenges.evaluators import get_challenge_handler
from app.modules.challenges.models import Challenge
from app.modules.challenges.schemas import (
    ChallengeAuthorOut,
    ChallengeCreate,
    ChallengePublicOut,
    ChallengeUpdate,
)
from app.modules.courses.models import Course, Lesson, LessonVersion, Module
from app.modules.tenants.models import OrganizationMember

router = APIRouter(tags=["challenges"])


def _scope_filter(organization_id: uuid.UUID | None):
    return Course.organization_id.is_(None) if organization_id is None else (Course.organization_id == organization_id)


def _to_author_out(ch: Challenge) -> ChallengeAuthorOut:
    return ChallengeAuthorOut(
        id=ch.id,
        lesson_version_id=ch.lesson_version_id,
        competency_id=ch.competency_id,
        challenge_type=ch.challenge_type,
        schema_version=ch.schema_version,
        order_index=ch.order_index,
        prompt=ch.prompt,
        payload_json=ch.payload_json,
        answer_key_json=ch.answer_key_json,
        pedagogical_explanation=ch.pedagogical_explanation,
        difficulty=ch.difficulty,
        points=ch.points,
        estimated_seconds=ch.estimated_seconds,
        is_safety_critical=ch.is_safety_critical,
        status=ch.status,
    )


def _get_scoped_lv(db: Session, lesson_version_id: uuid.UUID, organization_id: uuid.UUID | None) -> LessonVersion:
    row = db.execute(
        select(LessonVersion, Course)
        .join(Lesson, LessonVersion.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            LessonVersion.id == lesson_version_id,
            _scope_filter(organization_id),
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Versión de lección no encontrada en este ámbito")
    return row[0]


def _get_scoped_challenge(db: Session, challenge_id: uuid.UUID, organization_id: uuid.UUID | None) -> Challenge:
    row = db.execute(
        select(Challenge, Course)
        .join(LessonVersion, Challenge.lesson_version_id == LessonVersion.id)
        .join(Lesson, LessonVersion.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            Challenge.id == challenge_id,
            Challenge.deleted_at.is_(None),
            _scope_filter(organization_id),
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Reto no encontrado en este ámbito")
    return row[0]


def _create_challenge_impl(
    db: Session, *, lesson_version_id: uuid.UUID, organization_id: uuid.UUID | None, payload: ChallengeCreate
) -> ChallengeAuthorOut:
    lv = _get_scoped_lv(db, lesson_version_id, organization_id)
    handler = get_challenge_handler(payload.challenge_type, payload.schema_version)
    clean_payload, clean_answer_key = handler.validate_definition(payload.payload_json, payload.answer_key_json)

    ch = Challenge(
        lesson_version_id=lv.id,
        competency_id=payload.competency_id,
        challenge_type=payload.challenge_type,
        schema_version=payload.schema_version,
        order_index=payload.order_index,
        prompt=payload.prompt.strip(),
        payload_json=clean_payload,
        answer_key_json=clean_answer_key,
        pedagogical_explanation=payload.pedagogical_explanation.strip(),
        difficulty=payload.difficulty,
        points=payload.points,
        estimated_seconds=payload.estimated_seconds,
        is_safety_critical=payload.is_safety_critical,
        status="published" if lv.status == "published" else "draft",
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return _to_author_out(ch)


def _list_challenges_for_author_impl(
    db: Session, *, lesson_version_id: uuid.UUID, organization_id: uuid.UUID | None
) -> list[ChallengeAuthorOut]:
    _get_scoped_lv(db, lesson_version_id, organization_id)
    challenges = db.scalars(
        select(Challenge)
        .where(Challenge.lesson_version_id == lesson_version_id, Challenge.deleted_at.is_(None))
        .order_by(Challenge.order_index)
    ).all()
    return [_to_author_out(ch) for ch in challenges]


def _update_challenge_impl(
    db: Session, *, challenge_id: uuid.UUID, organization_id: uuid.UUID | None, payload: ChallengeUpdate
) -> ChallengeAuthorOut:
    ch = _get_scoped_challenge(db, challenge_id, organization_id)
    next_payload = payload.payload_json if payload.payload_json is not None else ch.payload_json
    next_answer_key = payload.answer_key_json if payload.answer_key_json is not None else ch.answer_key_json
    handler = get_challenge_handler(ch.challenge_type, ch.schema_version)
    clean_payload, clean_key = handler.validate_definition(next_payload, next_answer_key)

    ch.payload_json = clean_payload
    ch.answer_key_json = clean_key
    if payload.competency_id is not None:
        ch.competency_id = payload.competency_id
    if payload.order_index is not None:
        ch.order_index = payload.order_index
    if payload.prompt is not None:
        ch.prompt = payload.prompt.strip()
    if payload.pedagogical_explanation is not None:
        ch.pedagogical_explanation = payload.pedagogical_explanation.strip()
    if payload.difficulty is not None:
        ch.difficulty = payload.difficulty
    if payload.points is not None:
        ch.points = payload.points
    if payload.estimated_seconds is not None:
        ch.estimated_seconds = payload.estimated_seconds
    if payload.is_safety_critical is not None:
        ch.is_safety_critical = payload.is_safety_critical
    if payload.status is not None:
        ch.status = payload.status

    db.commit()
    db.refresh(ch)
    return _to_author_out(ch)


def _delete_challenge_impl(
    db: Session, *, challenge_id: uuid.UUID, organization_id: uuid.UUID | None
) -> None:
    ch = _get_scoped_challenge(db, challenge_id, organization_id)
    ch.deleted_at = datetime.now(timezone.utc)
    db.commit()


# ---------------------------------------------------------------------------
# Autoría CRUD Organizacional (Educador / Instructor / Coordinador)
# ---------------------------------------------------------------------------
@router.post(
    "/orgs/{org_id}/lesson-versions/{lesson_version_id}/challenges",
    response_model=ChallengeAuthorOut,
    status_code=status.HTTP_201_CREATED,
)
def create_org_challenge(
    lesson_version_id: uuid.UUID,
    payload: ChallengeCreate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> ChallengeAuthorOut:
    return _create_challenge_impl(
        db, lesson_version_id=lesson_version_id, organization_id=tenant.organization.id, payload=payload
    )


@router.get(
    "/orgs/{org_id}/lesson-versions/{lesson_version_id}/challenges",
    response_model=list[ChallengeAuthorOut],
)
def list_org_lesson_challenges_for_author(
    lesson_version_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> list[ChallengeAuthorOut]:
    return _list_challenges_for_author_impl(
        db, lesson_version_id=lesson_version_id, organization_id=tenant.organization.id
    )


@router.patch("/orgs/{org_id}/challenges/{challenge_id}", response_model=ChallengeAuthorOut)
def update_org_challenge(
    challenge_id: uuid.UUID,
    payload: ChallengeUpdate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> ChallengeAuthorOut:
    return _update_challenge_impl(
        db, challenge_id=challenge_id, organization_id=tenant.organization.id, payload=payload
    )


@router.delete("/orgs/{org_id}/challenges/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_org_challenge(
    challenge_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> Response:
    _delete_challenge_impl(db, challenge_id=challenge_id, organization_id=tenant.organization.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Autoría CRUD Global SuperAdmin
# ---------------------------------------------------------------------------
@router.post(
    "/admin/lesson-versions/{lesson_version_id}/challenges",
    response_model=ChallengeAuthorOut,
    status_code=status.HTTP_201_CREATED,
)
def create_global_challenge(
    lesson_version_id: uuid.UUID,
    payload: ChallengeCreate,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ChallengeAuthorOut:
    return _create_challenge_impl(db, lesson_version_id=lesson_version_id, organization_id=None, payload=payload)


@router.get(
    "/admin/lesson-versions/{lesson_version_id}/challenges",
    response_model=list[ChallengeAuthorOut],
)
def list_global_lesson_challenges_for_author(
    lesson_version_id: uuid.UUID,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[ChallengeAuthorOut]:
    return _list_challenges_for_author_impl(db, lesson_version_id=lesson_version_id, organization_id=None)


@router.patch("/admin/challenges/{challenge_id}", response_model=ChallengeAuthorOut)
def update_global_challenge(
    challenge_id: uuid.UUID,
    payload: ChallengeUpdate,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ChallengeAuthorOut:
    return _update_challenge_impl(db, challenge_id=challenge_id, organization_id=None, payload=payload)


@router.delete("/admin/challenges/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_global_challenge(
    challenge_id: uuid.UUID,
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Response:
    _delete_challenge_impl(db, challenge_id=challenge_id, organization_id=None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Lectura segura para el reproductor de estudiante
# ---------------------------------------------------------------------------
@router.get("/lesson-versions/{lesson_version_id}/challenges", response_model=list[ChallengePublicOut])
def list_lesson_challenges_for_player(
    lesson_version_id: uuid.UUID,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> list[ChallengePublicOut]:
    """Devuelve retos de una lección sin exponer answer_key_json."""
    row = db.execute(
        select(LessonVersion, Course)
        .join(Lesson, LessonVersion.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(LessonVersion.id == lesson_version_id, Course.deleted_at.is_(None))
    ).first()
    if not row:
        raise NotFoundError("Versión de lección no encontrada")

    lv, course = row
    if course.visibility != "public":
        if not current_user:
            raise ForbiddenError("Autenticación requerida para lecciones institucionales")
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
                raise ForbiddenError("No perteneces a la organización propietaria")

    challenges = db.scalars(
        select(Challenge)
        .where(
            Challenge.lesson_version_id == lv.id,
            Challenge.deleted_at.is_(None),
            Challenge.status == "published",
        )
        .order_by(Challenge.order_index)
    ).all()

    return [
        ChallengePublicOut(
            id=ch.id,
            lesson_version_id=ch.lesson_version_id,
            competency_id=ch.competency_id,
            challenge_type=ch.challenge_type,
            schema_version=ch.schema_version,
            order_index=ch.order_index,
            prompt=ch.prompt,
            payload_json=ch.payload_json,
            difficulty=ch.difficulty,
            points=ch.points,
            estimated_seconds=ch.estimated_seconds,
            is_safety_critical=ch.is_safety_critical,
            status=ch.status,
        )
        for ch in challenges
    ]
