"""Modelos de gamificación educativa: XP, rachas, energía configurable e insignias."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class StudentGamificationProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Perfil de XP, racha y energía configurable por ámbito."""

    __tablename__ = "student_gamification_profiles"
    __table_args__ = (
        CheckConstraint("total_xp >= 0", name="ck_sgp_xp"),
        CheckConstraint("current_streak_days >= 0", name="ck_sgp_streak"),
        CheckConstraint("longest_streak_days >= 0", name="ck_sgp_longest"),
        CheckConstraint("current_energy >= 0", name="ck_sgp_energy"),
        CheckConstraint("max_energy > 0", name="ck_sgp_max_energy"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    total_xp: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    current_streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_energy: Mapped[int] = mapped_column(SmallInteger, default=5, nullable=False)
    max_energy: Mapped[int] = mapped_column(SmallInteger, default=5, nullable=False)
    last_energy_refill_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


Index(
    "uq_gamification_profile_free",
    StudentGamificationProfile.user_id,
    unique=True,
    postgresql_where=text("organization_id IS NULL"),
    sqlite_where=text("organization_id IS NULL"),
)
Index(
    "uq_gamification_profile_org",
    StudentGamificationProfile.user_id,
    StudentGamificationProfile.organization_id,
    unique=True,
    postgresql_where=text("organization_id IS NOT NULL"),
    sqlite_where=text("organization_id IS NOT NULL"),
)


class XpTransaction(Base, UUIDPrimaryKeyMixin):
    """Libro mayor append-only de XP otorgado (separado de notas académicas)."""

    __tablename__ = "xp_transactions"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('challenge', 'lesson_bonus', 'review_session', 'streak_bonus', 'badge')",
            name="ck_xp_source",
        ),
        CheckConstraint("xp_amount > 0", name="ck_xp_amount_pos"),
        Index("idx_xp_transactions_org_classroom", "organization_id", "classroom_id", "user_id", "created_at"),
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
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    xp_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Badge(Base, UUIDPrimaryKeyMixin):
    """Insignias globales o institucionales."""

    __tablename__ = "badges"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    criteria_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Index(
    "uq_badges_global_code_active",
    func.lower(Badge.code),
    unique=True,
    postgresql_where=text("organization_id IS NULL AND deleted_at IS NULL"),
    sqlite_where=text("organization_id IS NULL AND deleted_at IS NULL"),
)
Index(
    "uq_badges_org_code_active",
    Badge.organization_id,
    func.lower(Badge.code),
    unique=True,
    postgresql_where=text("organization_id IS NOT NULL AND deleted_at IS NULL"),
    sqlite_where=text("organization_id IS NOT NULL AND deleted_at IS NULL"),
)


class StudentBadge(Base, UUIDPrimaryKeyMixin):
    """Insignias obtenidas por cada estudiante."""

    __tablename__ = "student_badges"
    __table_args__ = (UniqueConstraint("user_id", "badge_id", name="uq_student_badge"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    badge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("badges.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
