"""Motor de repetición espaciada SM-2 adaptado para microlearning y seguridad crítica."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.challenges.models import Challenge
from app.modules.spaced_repetition.models import SpacedRepetitionItem

SAFETY_CRITICAL_MAX_INTERVAL_DAYS = 45
NORMAL_MASTERED_MIN_REPS = 6
NORMAL_MASTERED_MIN_INTERVAL_DAYS = 90


def compute_quality_score(
    *,
    is_correct: bool,
    attempt_number: int,
    hints_used: int,
    response_time_ms: int | None,
    estimated_seconds: int,
) -> int:
    """Deriva calidad SM-2 (0..5) objetivamente desde el desempeño real."""
    if not is_correct:
        return 1 if attempt_number >= 2 else 2
    if hints_used > 0:
        return 3
    if response_time_ms is not None and response_time_ms > estimated_seconds * 1500:
        return 4
    return 5


def apply_sm2_step(
    *,
    ease_factor: Decimal,
    interval_days: int,
    repetitions: int,
    lapses: int,
    quality: int,
    is_safety_critical: bool,
    now: datetime,
) -> tuple[Decimal, int, int, int, str, datetime]:
    """Aplica transición SM-2 adaptada y devuelve nuevo estado."""
    ef_float = float(ease_factor)
    new_ef = ef_float + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(1.30, min(3.50, round(new_ef, 2)))
    new_ef_dec = Decimal(f"{new_ef:.2f}")

    if quality < 3:
        return (
            new_ef_dec,
            0,
            0,
            lapses + 1,
            "relearning",
            now + timedelta(minutes=10),
        )

    if repetitions == 0:
        new_interval = 1
    elif repetitions == 1:
        new_interval = 3
    else:
        new_interval = max(1, round(interval_days * new_ef))

    if is_safety_critical:
        new_interval = min(new_interval, SAFETY_CRITICAL_MAX_INTERVAL_DAYS)
        new_state = "review"
    else:
        if (repetitions + 1) >= NORMAL_MASTERED_MIN_REPS and new_interval >= NORMAL_MASTERED_MIN_INTERVAL_DAYS:
            new_state = "mastered"
        else:
            new_state = "review"

    return (
        new_ef_dec,
        new_interval,
        repetitions + 1,
        lapses,
        new_state,
        now + timedelta(days=new_interval),
    )


def record_challenge_review(
    db: Session,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    challenge: Challenge,
    is_correct: bool,
    attempt_number: int,
    hints_used: int,
    response_time_ms: int | None,
    now: datetime | None = None,
) -> SpacedRepetitionItem:
    """Actualiza o crea el ítem SM-2 tras un intento en el motor de retos."""
    ts = now or datetime.now(timezone.utc)
    quality = compute_quality_score(
        is_correct=is_correct,
        attempt_number=attempt_number,
        hints_used=hints_used,
        response_time_ms=response_time_ms,
        estimated_seconds=challenge.estimated_seconds,
    )

    item = db.scalar(
        select(SpacedRepetitionItem).where(
            SpacedRepetitionItem.user_id == user_id,
            SpacedRepetitionItem.challenge_id == challenge.id,
        )
    )
    if not item:
        item = SpacedRepetitionItem(
            user_id=user_id,
            organization_id=organization_id,
            challenge_id=challenge.id,
            ease_factor=Decimal("2.50"),
            interval_days=1,
            repetitions=0,
            lapses=0,
            item_state="learning",
            next_review_at=ts,
        )
        db.add(item)

    ef, interval_days, reps, lapses, state, next_at = apply_sm2_step(
        ease_factor=item.ease_factor,
        interval_days=item.interval_days,
        repetitions=item.repetitions,
        lapses=item.lapses,
        quality=quality,
        is_safety_critical=challenge.is_safety_critical,
        now=ts,
    )
    item.ease_factor = ef
    item.interval_days = interval_days
    item.repetitions = reps
    item.lapses = lapses
    item.last_quality = quality
    item.item_state = state
    item.last_reviewed_at = ts
    item.next_review_at = next_at
    return item
