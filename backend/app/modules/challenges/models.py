"""Modelos de retos polimórficos, Banco de Preguntas reutilizable y entregas abiertas con rúbrica."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, SmallInteger, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Challenge(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reto interactivo perteneciente a una versión de lección."""

    __tablename__ = "challenges"
    __table_args__ = (
        CheckConstraint(
            "challenge_type IN ('visual_concept_card', 'matching', 'sequence_ordering', 'interactive_zones', 'decision_simulation', 'fill_in_blanks', 'open_response')",
            name="ck_challenge_type",
        ),
        CheckConstraint("schema_version > 0", name="ck_challenge_schema_ver"),
        CheckConstraint("order_index >= 0", name="ck_challenge_order"),
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_challenge_difficulty"),
        CheckConstraint("points > 0", name="ck_challenge_points"),
        CheckConstraint("estimated_seconds > 0", name="ck_challenge_est_sec"),
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_challenge_status"),
    )

    lesson_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lesson_versions.id", ondelete="CASCADE"), nullable=False
    )
    competency_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("competencies.id", ondelete="SET NULL"), nullable=True
    )
    challenge_type: Mapped[str] = mapped_column(String(40), nullable=False)
    schema_version: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONType, nullable=False)
    answer_key_json: Mapped[dict] = mapped_column(JSONType, nullable=False)
    pedagogical_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[int] = mapped_column(SmallInteger, default=2, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    estimated_seconds: Mapped[int] = mapped_column(SmallInteger, default=45, nullable=False)
    is_safety_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QuestionBankItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Ítem reutilizable del Banco de Preguntas para sorteos y exámenes aleatorios."""

    __tablename__ = "question_bank_items"
    __table_args__ = (
        CheckConstraint(
            "challenge_type IN ('visual_concept_card', 'matching', 'sequence_ordering', 'interactive_zones', 'decision_simulation', 'fill_in_blanks', 'open_response')",
            name="ck_qbank_type",
        ),
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_qbank_difficulty"),
        CheckConstraint("points > 0", name="ck_qbank_points"),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    competency_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("competencies.id", ondelete="SET NULL"), nullable=True
    )
    topic_tag: Mapped[str] = mapped_column(String(80), default="general", nullable=False)
    challenge_type: Mapped[str] = mapped_column(String(40), nullable=False)
    schema_version: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONType, nullable=False)
    answer_key_json: Mapped[dict] = mapped_column(JSONType, nullable=False)
    pedagogical_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[int] = mapped_column(SmallInteger, default=2, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    estimated_seconds: Mapped[int] = mapped_column(SmallInteger, default=45, nullable=False)
    is_safety_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OpenSubmission(Base, UUIDPrimaryKeyMixin):
    """Entrega de respuesta abierta / ensayo con pre-evaluación IA y calificación docente."""

    __tablename__ = "open_submissions"
    __table_args__ = (
        CheckConstraint("status IN ('pending_review', 'graded')", name="ck_open_sub_status"),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_points: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    ai_suggested_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    teacher_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending_review", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
