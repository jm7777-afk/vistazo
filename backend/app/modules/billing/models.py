"""Modelos SaaS de suscripciones y límites por organización."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationSubscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Plan SaaS activo y cuotas asignadas a una organización."""

    __tablename__ = "organization_subscriptions"
    __table_args__ = (
        CheckConstraint("plan_code IN ('free', 'educator_pro', 'institution')", name="ck_sub_plan_code"),
        CheckConstraint("status IN ('active', 'trialing', 'past_due', 'canceled')", name="ck_sub_status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    plan_code: Mapped[str] = mapped_column(String(30), default="free", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    max_students: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    monthly_ai_limit: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    external_customer_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_subscription_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
