"""Endpoints de repetición espaciada, sesiones de repaso y recuperación de energía."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.challenges.models import Challenge
from app.modules.gamification.service import grant_energy_recovery_and_xp
from app.modules.spaced_repetition.models import ReviewSession, ReviewSessionItem, SpacedRepetitionItem

router = APIRouter(prefix="/reviews", tags=["spaced_repetition"])


class DueReviewItemOut(BaseModel):
    sr_item_id: uuid.UUID
    challenge_id: uuid.UUID
    challenge_type: str
    prompt: str
    payload_json: dict
    points: int
    estimated_seconds: int
    is_safety_critical: bool
    item_state: str
    interval_days: int
    lapses: int
    next_review_at: datetime


class StartSessionRequest(BaseModel):
    organization_id: uuid.UUID | None = None
    session_mode: Literal["spaced_repetition", "flash_training", "energy_recovery"] = "spaced_repetition"
    limit: int = Field(default=5, ge=1, le=20)


class ReviewSessionOut(BaseModel):
    session_id: uuid.UUID
    session_mode: str
    items_planned: int
    items_completed: int
    energy_recovered: int
    items: list[DueReviewItemOut] = Field(default_factory=list)


class CompleteSessionRequest(BaseModel):
    items_completed: int = Field(ge=0, le=50)


@router.get("/due", response_model=list[DueReviewItemOut])
def list_due_reviews(
    organization_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DueReviewItemOut]:
    now = datetime.now(timezone.utc)
    stmt = (
        select(SpacedRepetitionItem, Challenge)
        .join(Challenge, SpacedRepetitionItem.challenge_id == Challenge.id)
        .where(
            SpacedRepetitionItem.user_id == current_user.id,
            SpacedRepetitionItem.item_state != "mastered",
            SpacedRepetitionItem.next_review_at <= now,
            Challenge.deleted_at.is_(None),
            Challenge.status == "published",
        )
        .order_by(SpacedRepetitionItem.next_review_at.asc())
        .limit(limit)
    )
    if organization_id is not None:
        stmt = stmt.where(SpacedRepetitionItem.organization_id == organization_id)

    rows = db.execute(stmt).all()
    return [
        DueReviewItemOut(
            sr_item_id=sr.id,
            challenge_id=ch.id,
            challenge_type=ch.challenge_type,
            prompt=ch.prompt,
            payload_json=ch.payload_json,
            points=ch.points,
            estimated_seconds=ch.estimated_seconds,
            is_safety_critical=ch.is_safety_critical,
            item_state=sr.item_state,
            interval_days=sr.interval_days,
            lapses=sr.lapses,
            next_review_at=sr.next_review_at,
        )
        for sr, ch in rows
    ]


@router.post("/sessions", response_model=ReviewSessionOut, status_code=status.HTTP_201_CREATED)
def start_review_session(
    payload: StartSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewSessionOut:
    stmt = (
        select(SpacedRepetitionItem, Challenge)
        .join(Challenge, SpacedRepetitionItem.challenge_id == Challenge.id)
        .where(
            SpacedRepetitionItem.user_id == current_user.id,
            Challenge.deleted_at.is_(None),
            Challenge.status == "published",
        )
        .order_by(SpacedRepetitionItem.next_review_at.asc())
        .limit(payload.limit)
    )
    if payload.organization_id is not None:
        stmt = stmt.where(SpacedRepetitionItem.organization_id == payload.organization_id)

    rows = db.execute(stmt).all()
    session_row = ReviewSession(
        user_id=current_user.id,
        organization_id=payload.organization_id,
        session_mode=payload.session_mode,
        items_planned=len(rows),
    )
    db.add(session_row)
    db.flush()

    out_items: list[DueReviewItemOut] = []
    for idx, (sr, ch) in enumerate(rows):
        db.add(
            ReviewSessionItem(
                review_session_id=session_row.id,
                spaced_repetition_item_id=sr.id,
                order_index=idx,
            )
        )
        out_items.append(
            DueReviewItemOut(
                sr_item_id=sr.id,
                challenge_id=ch.id,
                challenge_type=ch.challenge_type,
                prompt=ch.prompt,
                payload_json=ch.payload_json,
                points=ch.points,
                estimated_seconds=ch.estimated_seconds,
                is_safety_critical=ch.is_safety_critical,
                item_state=sr.item_state,
                interval_days=sr.interval_days,
                lapses=sr.lapses,
                next_review_at=sr.next_review_at,
            )
        )

    db.commit()
    return ReviewSessionOut(
        session_id=session_row.id,
        session_mode=session_row.session_mode,
        items_planned=session_row.items_planned,
        items_completed=0,
        energy_recovered=0,
        items=out_items,
    )


@router.post("/sessions/{session_id}/complete", response_model=ReviewSessionOut)
def complete_review_session(
    session_id: uuid.UUID,
    payload: CompleteSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewSessionOut:
    session_row = db.scalar(
        select(ReviewSession).where(ReviewSession.id == session_id, ReviewSession.user_id == current_user.id)
    )
    if not session_row:
        raise NotFoundError("Sesión de repaso no encontrada")

    session_row.items_completed = payload.items_completed
    session_row.completed_at = datetime.now(timezone.utc)
    recovered = 0
    if session_row.session_mode == "energy_recovery" and payload.items_completed > 0:
        recovered = grant_energy_recovery_and_xp(
            db,
            user_id=current_user.id,
            organization_id=session_row.organization_id,
            session_id=session_row.id,
            energy_gain=2,
            xp_gain=15,
        )
    elif payload.items_completed > 0:
        grant_energy_recovery_and_xp(
            db,
            user_id=current_user.id,
            organization_id=session_row.organization_id,
            session_id=session_row.id,
            energy_gain=0,
            xp_gain=15,
        )

    session_row.energy_recovered = recovered
    db.commit()
    return ReviewSessionOut(
        session_id=session_row.id,
        session_mode=session_row.session_mode,
        items_planned=session_row.items_planned,
        items_completed=session_row.items_completed,
        energy_recovered=session_row.energy_recovered,
        items=[],
    )
