"""Endpoints de autoría y lectura segura de retos por versión de lección."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_optional_user, require_permission
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.challenges.evaluators import get_challenge_handler
from app.modules.challenges.models import Challenge
from app.modules.challenges.schemas import ChallengeAuthorOut, ChallengeCreate, ChallengePublicOut
from app.modules.courses.models import Course, Lesson, LessonVersion, Module
from app.modules.tenants.models import OrganizationMember

router = APIRouter(tags=["challenges"])


@router.post(
    "/orgs/{org_id}/lesson-versions/{lesson_version_id}/challenges",
    response_model=ChallengeAuthorOut,
    status_code=status.HTTP_201_CREATED,
)
def create_challenge(
    lesson_version_id: uuid.UUID,
    payload: ChallengeCreate,
    tenant: TenantContext = Depends(require_permission("lesson:author")),
    db: Session = Depends(get_db),
) -> ChallengeAuthorOut:
    row = db.execute(
        select(LessonVersion, Course)
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

    lv, _course = row
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
