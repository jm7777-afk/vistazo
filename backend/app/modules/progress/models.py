"""Modelos de intentos de retos, progreso por lección y competencias del estudiante."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class ChallengeAttempt(Base, UUIDPrimaryKeyMixin):
    """Historial inmutable de intentos realizados por un estudiante."""

    __tablename__ = "challenge_attempts"
    __table_args__ = (
        CheckConstraint("score_awarded >= 0", name="ck_attempt_score_nonneg"),
        CheckConstraint("hints_used >= 0", name="ck_attempt_hints_nonneg"),
        CheckConstraint("attempt_number > 0", name="ck_attempt_num_pos"),
        Index("idx_attempts_user_challenge_time", "user_id", "challenge_id", "created_at"),
        Index("idx_attempts_org_classroom_time", "organization_id", "classroom_id", "created_at"),
    )

    client_attempt_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), unique=True, nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("classrooms.id", ondelete="SET NULL"), nullable=True
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    submitted_answer_json: Mapped[dict] = mapped_column(JSONType, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hints_used: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class LessonProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Progreso consolidado del estudiante por versión de lección y contexto."""

    __tablename__ = "lesson_progress"
    __table_args__ = (
        CheckConstraint("status IN ('not_started', 'in_progress', 'completed')", name="ck_lp_status"),
        CheckConstraint("best_score_pct >= 0 AND best_score_pct <= 100", name="ck_lp_score_pct"),
        Index("idx_lesson_progress_student", "user_id", "status", "last_activity_at"),
        Index("idx_lesson_progress_classroom", "organization_id", "classroom_id", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("classrooms.id", ondelete="SET NULL"), nullable=True
    )
    lesson_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lesson_versions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)
    best_score_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    completed_challenges: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_challenges: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


Index(
    "uq_lesson_progress_free",
    LessonProgress.user_id,
    LessonProgress.lesson_version_id,
    unique=True,
    postgresql_where=text("classroom_id IS NULL"),
    sqlite_where=text("classroom_id IS NULL"),
)
Index(
    "uq_lesson_progress_classroom",
    LessonProgress.user_id,
    LessonProgress.lesson_version_id,
    LessonProgress.classroom_id,
    unique=True,
    postgresql_where=text("classroom_id IS NOT NULL"),
    sqlite_where=text("classroom_id IS NOT NULL"),
)


class StudentCompetency(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Nivel de dominio de competencia acumulado por estudiante y ámbito."""

    __tablename__ = "student_competencies"
    __table_args__ = (
        CheckConstraint("mastery_score >= 0 AND mastery_score <= 100", name="ck_sc_score"),
        CheckConstraint("mastery_status IN ('not_started', 'in_progress', 'achieved', 'needs_refresh')", name="ck_sc_status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    competency_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("competencies.id", ondelete="CASCADE"), nullable=False
    )
    mastery_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    evaluated_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mastery_status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)
    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


Index(
    "uq_student_comp_free",
    StudentCompetency.user_id,
    StudentCompetency.competency_id,
    unique=True,
    postgresql_where=text("organization_id IS NULL"),
    sqlite_where=text("organization_id IS NULL"),
)
Index(
    "uq_student_comp_org",
    StudentCompetency.user_id,
    StudentCompetency.competency_id,
    StudentCompetency.organization_id,
    unique=True,
    postgresql_where=text("organization_id IS NOT NULL"),
    sqlite_where=text("organization_id IS NOT NULL"),
)
