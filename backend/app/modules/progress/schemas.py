"""Esquemas Pydantic de intentos, evaluación en backend y progreso."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SubmitAttemptRequest(BaseModel):
    client_attempt_id: uuid.UUID | None = None
    classroom_id: uuid.UUID | None = None
    submitted_answer: dict
    response_time_ms: int | None = Field(default=None, ge=0)
    hints_used: int = Field(default=0, ge=0, le=20)


class SubmitAttemptResponse(BaseModel):
    attempt_id: uuid.UUID
    challenge_id: uuid.UUID
    is_correct: bool
    score_awarded: int
    max_points: int
    pedagogical_explanation: str
    detail: dict
    lesson_status: str
    lesson_score_pct: Decimal
    completed_challenges: int
    total_challenges: int
    xp_awarded: int = 0
    next_review_at: datetime | None = None
    unlocked_library_items: int = 0


class LessonProgressOut(BaseModel):
    id: uuid.UUID
    lesson_version_id: uuid.UUID
    classroom_id: uuid.UUID | None
    organization_id: uuid.UUID | None
    status: str
    best_score_pct: Decimal
    completed_challenges: int
    total_challenges: int
    completed_at: datetime | None
    last_activity_at: datetime


class StudentCompetencyOut(BaseModel):
    competency_id: uuid.UUID
    organization_id: uuid.UUID | None
    mastery_score: Decimal
    evaluated_attempts: int
    mastery_status: str
    last_evaluated_at: datetime


class StudentProgressOverview(BaseModel):
    lessons: list[LessonProgressOut]
    competencies: list[StudentCompetencyOut]
