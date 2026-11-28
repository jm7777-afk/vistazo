"""Endpoints de Clase en Vivo (Live Quiz Kahoot-style) para aulas y sesiones globales."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_optional_user, require_permission, require_super_admin
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationDomainError
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.challenges.evaluators import get_challenge_handler
from app.modules.challenges.models import Challenge
from app.modules.challenges.schemas import ChallengePublicOut
from app.modules.courses.models import Course, Lesson, LessonVersion, Module
from app.modules.live_quiz.models import LiveQuizParticipant, LiveQuizSession

router = APIRouter(tags=["live_quiz"])


class LiveSessionCreate(BaseModel):
    lesson_version_id: uuid.UUID
    classroom_id: uuid.UUID | None = None
    title: str = Field(min_length=2, max_length=200)


class LiveParticipantOut(BaseModel):
    id: uuid.UUID
    display_name: str
    score: int
    answered_count: int
    correct_count: int


class LiveSessionStateOut(BaseModel):
    id: uuid.UUID
    room_code: str
    title: str
    status: str
    current_index: int
    total_challenges: int
    current_challenge: ChallengePublicOut | None
    leaderboard: list[LiveParticipantOut]


class LiveJoinRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)


class LiveJoinResponse(BaseModel):
    participant_id: uuid.UUID
    room_code: str
    display_name: str


class LiveAnswerRequest(BaseModel):
    participant_id: uuid.UUID
    submitted_answer: dict


class LiveAnswerResponse(BaseModel):
    is_correct: bool
    points_awarded: int
    explanation: str
    new_score: int


def _new_room_code() -> str:
    return "LIVE-" + "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(4))


def _create_live_session_impl(
    db: Session,
    *,
    organization_id: uuid.UUID | None,
    host_user_id: uuid.UUID,
    payload: LiveSessionCreate,
) -> LiveSessionStateOut:
    cond = Course.organization_id.is_(None) if organization_id is None else (Course.organization_id == organization_id)
    row = db.execute(
        select(LessonVersion, Course)
        .join(Lesson, LessonVersion.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(LessonVersion.id == payload.lesson_version_id, cond, Course.deleted_at.is_(None))
    ).first()
    if not row:
        raise NotFoundError("Versión de lección no encontrada para iniciar sala en vivo")

    challenges = db.scalars(
        select(Challenge)
        .where(Challenge.lesson_version_id == payload.lesson_version_id, Challenge.deleted_at.is_(None))
        .order_by(Challenge.order_index)
    ).all()
    if not challenges:
        raise ValidationDomainError("La lección debe tener al menos 1 reto antes de lanzar clase en vivo")

    session_row = LiveQuizSession(
        organization_id=organization_id,
        classroom_id=payload.classroom_id,
        lesson_version_id=payload.lesson_version_id,
        host_user_id=host_user_id,
        room_code=_new_room_code(),
        title=payload.title.strip(),
        status="waiting",
        current_index=0,
    )
    db.add(session_row)
    db.commit()
    db.refresh(session_row)
    return _build_room_state(db, session_row)


def _build_room_state(db: Session, room: LiveQuizSession) -> LiveSessionStateOut:
    challenges = db.scalars(
        select(Challenge)
        .where(Challenge.lesson_version_id == room.lesson_version_id, Challenge.deleted_at.is_(None))
        .order_by(Challenge.order_index)
    ).all()
    current_public: ChallengePublicOut | None = None
    if room.status == "active" and 0 <= room.current_index < len(challenges):
        ch = challenges[room.current_index]
        current_public = ChallengePublicOut(
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
    participants = db.scalars(
        select(LiveQuizParticipant)
        .where(LiveQuizParticipant.session_id == room.id)
        .order_by(LiveQuizParticipant.score.desc(), LiveQuizParticipant.joined_at.asc())
    ).all()
    return LiveSessionStateOut(
        id=room.id,
        room_code=room.room_code,
        title=room.title,
        status=room.status,
        current_index=room.current_index,
        total_challenges=len(challenges),
        current_challenge=current_public,
        leaderboard=[
            LiveParticipantOut(
                id=p.id,
                display_name=p.display_name,
                score=p.score,
                answered_count=p.answered_count,
                correct_count=p.correct_count,
            )
            for p in participants
        ],
    )


@router.post("/orgs/{org_id}/live-sessions", response_model=LiveSessionStateOut, status_code=status.HTTP_201_CREATED)
def create_org_live_session(
    payload: LiveSessionCreate,
    tenant: TenantContext = Depends(require_permission("classroom:view_assigned")),
    db: Session = Depends(get_db),
) -> LiveSessionStateOut:
    return _create_live_session_impl(
        db, organization_id=tenant.organization.id, host_user_id=tenant.user.id, payload=payload
    )


@router.post("/admin/live-sessions", response_model=LiveSessionStateOut, status_code=status.HTTP_201_CREATED)
def create_global_live_session(
    payload: LiveSessionCreate,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> LiveSessionStateOut:
    return _create_live_session_impl(db, organization_id=None, host_user_id=admin.id, payload=payload)


@router.get("/live-sessions/{room_code}", response_model=LiveSessionStateOut)
def get_live_session_state(room_code: str, db: Session = Depends(get_db)) -> LiveSessionStateOut:
    room = db.scalar(select(LiveQuizSession).where(LiveQuizSession.room_code == room_code.strip().upper()))
    if not room:
        raise NotFoundError("Sala en vivo no encontrada")
    return _build_room_state(db, room)


@router.post("/live-sessions/{room_code}/join", response_model=LiveJoinResponse, status_code=status.HTTP_201_CREATED)
def join_live_session(
    room_code: str,
    payload: LiveJoinRequest,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> LiveJoinResponse:
    room = db.scalar(select(LiveQuizSession).where(LiveQuizSession.room_code == room_code.strip().upper()))
    if not room or room.status == "finished":
        raise NotFoundError("Sala no disponible o ya finalizada")
    part = LiveQuizParticipant(
        session_id=room.id,
        user_id=current_user.id if current_user else None,
        display_name=payload.display_name.strip(),
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return LiveJoinResponse(participant_id=part.id, room_code=room.room_code, display_name=part.display_name)


@router.post("/live-sessions/{room_code}/advance", response_model=LiveSessionStateOut)
def advance_live_session(
    room_code: str,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> LiveSessionStateOut:
    if not current_user:
        raise ForbiddenError("Solo el anfitrión autenticado puede avanzar la sala")
    room = db.scalar(select(LiveQuizSession).where(LiveQuizSession.room_code == room_code.strip().upper()))
    if not room:
        raise NotFoundError("Sala no encontrada")
    if not current_user.is_super_admin and room.host_user_id != current_user.id:
        raise ForbiddenError("Solo quien inició la sala puede controlar las preguntas")

    total = len(
        db.scalars(
            select(Challenge.id).where(
                Challenge.lesson_version_id == room.lesson_version_id, Challenge.deleted_at.is_(None)
            )
        ).all()
    )
    if room.status == "waiting":
        room.status = "active"
        room.current_index = 0
    elif room.status == "active":
        if room.current_index + 1 < total:
            room.current_index += 1
        else:
            room.status = "finished"
            room.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(room)
    return _build_room_state(db, room)


@router.post("/live-sessions/{room_code}/answer", response_model=LiveAnswerResponse)
def submit_live_answer(
    room_code: str,
    payload: LiveAnswerRequest,
    db: Session = Depends(get_db),
) -> LiveAnswerResponse:
    room = db.scalar(select(LiveQuizSession).where(LiveQuizSession.room_code == room_code.strip().upper()))
    if not room or room.status != "active":
        raise ValidationDomainError("La sala no está aceptando respuestas en este momento")

    participant = db.scalar(
        select(LiveQuizParticipant).where(
            LiveQuizParticipant.id == payload.participant_id, LiveQuizParticipant.session_id == room.id
        )
    )
    if not participant:
        raise NotFoundError("Participante no registrado en la sala")
    if participant.last_answered_index == room.current_index:
        raise ConflictError("Ya respondiste la pregunta actual")

    challenges = db.scalars(
        select(Challenge)
        .where(Challenge.lesson_version_id == room.lesson_version_id, Challenge.deleted_at.is_(None))
        .order_by(Challenge.order_index)
    ).all()
    if room.current_index >= len(challenges):
        raise ValidationDomainError("No hay pregunta activa")
    ch = challenges[room.current_index]

    handler = get_challenge_handler(ch.challenge_type, ch.schema_version)
    result = handler.evaluate(
        payload_raw=ch.payload_json,
        answer_key_raw=ch.answer_key_json,
        submission_raw=payload.submitted_answer,
        max_points=ch.points,
        is_safety_critical=ch.is_safety_critical,
    )

    awarded = result.score_awarded
    participant.score += awarded
    participant.answered_count += 1
    if result.is_correct:
        participant.correct_count += 1
    participant.last_answered_index = room.current_index
    db.commit()
    db.refresh(participant)
    return LiveAnswerResponse(
        is_correct=result.is_correct,
        points_awarded=awarded,
        explanation=ch.pedagogical_explanation,
        new_score=participant.score,
    )
