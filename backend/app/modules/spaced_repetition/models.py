"""Modelos de repetición espaciada (SM-2) y sesiones de repaso."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, SmallInteger, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class SpacedRepetitionItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Estado SM-2 por estudiante y reto."""

    __tablename__ = "spaced_repetition_items"
    __table_args__ = (
        CheckConstraint("ease_factor >= 1.30 AND ease_factor <= 3.50", name="ck_sr_ease"),
        CheckConstraint("interval_days >= 0", name="ck_sr_interval"),
        CheckConstraint("repetitions >= 0", name="ck_sr_reps"),
        CheckConstraint("lapses >= 0", name="ck_sr_lapses"),
        CheckConstraint("last_quality IS NULL OR (last_quality >= 0 AND last_quality <= 5)", name="ck_sr_quality"),
        CheckConstraint("item_state IN ('learning', 'review', 'relearning', 'mastered')", name="ck_sr_state"),
        UniqueConstraint("user_id", "challenge_id", name="uq_sr_user_challenge"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    ease_factor: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2.50"), nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lapses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_quality: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    item_state: Mapped[str] = mapped_column(String(20), default="learning", nullable=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


Index(
    "idx_sr_items_pending_due",
    SpacedRepetitionItem.user_id,
    SpacedRepetitionItem.next_review_at,
    postgresql_where=text("item_state <> 'mastered'"),
    sqlite_where=text("item_state <> 'mastered'"),
)


class ReviewSession(Base, UUIDPrimaryKeyMixin):
    """Sesión de repaso activo, entrenamiento flash o recuperación de energía."""

    __tablename__ = "review_sessions"
    __table_args__ = (
        CheckConstraint(
            "session_mode IN ('spaced_repetition', 'flash_training', 'energy_recovery')",
            name="ck_review_session_mode",
        ),
        Index("idx_review_sessions_user", "user_id", "started_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    session_mode: Mapped[str] = mapped_column(String(30), default="spaced_repetition", nullable=False)
    items_planned: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    items_completed: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    energy_recovered: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewSessionItem(Base):
    """Ítems planificados dentro de una sesión de repaso."""

    __tablename__ = "review_session_items"

    review_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("review_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    spaced_repetition_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("spaced_repetition_items.id", ondelete="CASCADE"), primary_key=True
    )
    challenge_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("challenge_attempts.id", ondelete="SET NULL"), nullable=True
    )
    order_index: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
