"""Modelo de retos interactivos polimórficos por versión de lección."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, SmallInteger, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin


class Challenge(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reto interactivo perteneciente a una versión de lección."""

    __tablename__ = "challenges"
    __table_args__ = (
        CheckConstraint(
            "challenge_type IN ('visual_concept_card', 'matching', 'sequence_ordering', 'interactive_zones', 'decision_simulation', 'fill_in_blanks')",
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
