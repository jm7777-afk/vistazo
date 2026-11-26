"""Analíticas pedagógicas por aula para instructores asignados y coordinadores."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, require_permission
from app.db.session import get_db
from app.modules.challenges.models import Challenge
from app.modules.curriculum.models import ClassroomMember
from app.modules.curriculum.router import _ensure_classroom_access
from app.modules.progress.models import ChallengeAttempt, LessonProgress

router = APIRouter(prefix="/orgs/{org_id}/analytics", tags=["analytics"])


class HardChallengeStat(BaseModel):
    challenge_id: uuid.UUID
    prompt: str
    challenge_type: str
    total_attempts: int
    error_rate_pct: float


class ClassroomAnalyticsOut(BaseModel):
    classroom_id: uuid.UUID
    classroom_name: str
    enrolled_students: int
    completed_lesson_records: int
    avg_lesson_score_pct: float
    total_challenge_attempts: int
    overall_accuracy_pct: float
    hardest_challenges: list[HardChallengeStat]


@router.get("/classrooms/{classroom_id}", response_model=ClassroomAnalyticsOut)
def get_classroom_analytics(
    classroom_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("classroom:view_assigned")),
    db: Session = Depends(get_db),
) -> ClassroomAnalyticsOut:
    classroom = _ensure_classroom_access(db, tenant, classroom_id)

    enrolled_students = db.scalar(
        select(func.count(ClassroomMember.id)).where(
            ClassroomMember.classroom_id == classroom.id,
            ClassroomMember.deleted_at.is_(None),
            ClassroomMember.enrollment_status == "enrolled",
        )
    ) or 0

    lp_rows = db.scalars(
        select(LessonProgress).where(LessonProgress.classroom_id == classroom.id)
    ).all()
    completed_lessons = sum(1 for l in lp_rows if l.status == "completed")
    avg_score = round(sum(float(l.best_score_pct) for l in lp_rows) / len(lp_rows), 2) if lp_rows else 0.0

    attempt_stats = db.execute(
        select(
            func.count(ChallengeAttempt.id),
            func.coalesce(func.sum(case((ChallengeAttempt.is_correct.is_(True), 1), else_=0)), 0),
        ).where(ChallengeAttempt.classroom_id == classroom.id)
    ).one()
    total_attempts = int(attempt_stats[0] or 0)
    correct_attempts = int(attempt_stats[1] or 0)
    accuracy = round((correct_attempts / total_attempts) * 100, 2) if total_attempts else 0.0

    challenge_rows = db.execute(
        select(
            Challenge.id,
            Challenge.prompt,
            Challenge.challenge_type,
            func.count(ChallengeAttempt.id).label("attempts"),
            func.coalesce(func.sum(case((ChallengeAttempt.is_correct.is_(False), 1), else_=0)), 0).label("errors"),
        )
        .join(ChallengeAttempt, ChallengeAttempt.challenge_id == Challenge.id)
        .where(ChallengeAttempt.classroom_id == classroom.id)
        .group_by(Challenge.id, Challenge.prompt, Challenge.challenge_type)
        .order_by(func.count(ChallengeAttempt.id).desc())
        .limit(5)
    ).all()

    hardest = [
        HardChallengeStat(
            challenge_id=r.id,
            prompt=r.prompt,
            challenge_type=r.challenge_type,
            total_attempts=int(r.attempts),
            error_rate_pct=round((int(r.errors) / int(r.attempts)) * 100, 2) if r.attempts else 0.0,
        )
        for r in challenge_rows
    ]

    return ClassroomAnalyticsOut(
        classroom_id=classroom.id,
        classroom_name=classroom.name,
        enrolled_students=int(enrolled_students),
        completed_lesson_records=completed_lessons,
        avg_lesson_score_pct=avg_score,
        total_challenge_attempts=total_attempts,
        overall_accuracy_pct=accuracy,
        hardest_challenges=hardest,
    )
