"""Modelos de suscripciones de notificaciones Push PWA."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONType, UUIDPrimaryKeyMixin, utcnow


class PushSubscription(Base, UUIDPrimaryKeyMixin):
    """Suscripción Web Push / dispositivo para recordatorios de racha y SM-2."""

    __tablename__ = "push_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    subscription_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    device_label: Mapped[str] = mapped_column(String(120), default="Web PWA", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
