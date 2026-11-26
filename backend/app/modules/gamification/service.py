"""Servicios de gamificación educativa: XP, rachas, energía configurable e insignias."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.gamification.models import Badge, StudentBadge, StudentGamificationProfile, XpTransaction


def get_or_create_profile(
    db: Session,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    max_energy: int = 5,
) -> StudentGamificationProfile:
    scope_filter = (
        StudentGamificationProfile.organization_id == organization_id
        if organization_id is not None
        else StudentGamificationProfile.organization_id.is_(None)
    )
    profile = db.scalar(
        select(StudentGamificationProfile).where(StudentGamificationProfile.user_id == user_id, scope_filter)
    )
    if not profile:
        profile = StudentGamificationProfile(
            user_id=user_id,
            organization_id=organization_id,
            total_xp=0,
            current_streak_days=0,
            longest_streak_days=0,
            current_energy=max_energy,
            max_energy=max_energy,
        )
        db.add(profile)
        db.flush()
    return profile


def _update_streak(profile: StudentGamificationProfile, today: date) -> None:
    if profile.last_active_date == today:
        return
    if profile.last_active_date == today - timedelta(days=1):
        profile.current_streak_days += 1
    else:
        profile.current_streak_days = 1
    profile.longest_streak_days = max(profile.longest_streak_days, profile.current_streak_days)
    profile.last_active_date = today


def apply_challenge_gamification(
    db: Session,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    classroom_id: uuid.UUID | None,
    challenge_id: uuid.UUID,
    is_correct: bool,
    score_awarded: int,
    is_safety_critical: bool,
    energy_enabled: bool,
    max_energy: int,
    lesson_just_completed: bool,
) -> StudentGamificationProfile:
    """Actualiza XP, racha, energía e insignias sin alterar calificaciones académicas."""
    profile = get_or_create_profile(db, user_id=user_id, organization_id=organization_id, max_energy=max_energy)
    today = datetime.now(timezone.utc).date()
    _update_streak(profile, today)

    if is_correct and score_awarded > 0:
        profile.total_xp += score_awarded
        db.add(
            XpTransaction(
                user_id=user_id,
                organization_id=organization_id,
                classroom_id=classroom_id,
                source_type="challenge",
                source_id=challenge_id,
                xp_amount=score_awarded,
            )
        )
    elif not is_correct and energy_enabled and not is_safety_critical:
        # Nunca penaliza energía en actividades de rescate/seguridad crítica
        if profile.current_energy > 0:
            profile.current_energy -= 1

    if lesson_just_completed:
        profile.total_xp += 25
        db.add(
            XpTransaction(
                user_id=user_id,
                organization_id=organization_id,
                classroom_id=classroom_id,
                source_type="lesson_bonus",
                source_id=challenge_id,
                xp_amount=25,
            )
        )
        # Otorga insignia si existe FIRST_RESCUE_LESSON
        badge = db.scalar(
            select(Badge).where(Badge.code == "FIRST_RESCUE_LESSON", Badge.deleted_at.is_(None))
        )
        if badge:
            already = db.scalar(
                select(StudentBadge).where(StudentBadge.user_id == user_id, StudentBadge.badge_id == badge.id)
            )
            if not already:
                db.add(StudentBadge(user_id=user_id, badge_id=badge.id, organization_id=organization_id))

    return profile


def grant_energy_recovery_and_xp(
    db: Session,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    session_id: uuid.UUID,
    energy_gain: int,
    xp_gain: int,
) -> int:
    """Recupera energía tras completar repaso en biblioteca y suma XP de repaso."""
    profile = get_or_create_profile(db, user_id=user_id, organization_id=organization_id)
    _update_streak(profile, datetime.now(timezone.utc).date())
    before = profile.current_energy
    profile.current_energy = min(profile.max_energy, profile.current_energy + energy_gain)
    profile.last_energy_refill_at = datetime.now(timezone.utc)
    if xp_gain > 0:
        profile.total_xp += xp_gain
        db.add(
            XpTransaction(
                user_id=user_id,
                organization_id=organization_id,
                source_type="review_session",
                source_id=session_id,
                xp_amount=xp_gain,
            )
        )
    return profile.current_energy - before
