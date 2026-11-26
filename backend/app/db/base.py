"""Base declarativa SQLAlchemy 2.x y mixins reutilizables."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Devuelve timestamp UTC con zona horaria."""
    return datetime.now(timezone.utc)


JSONType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    """Clase base para todos los modelos ORM."""

    pass


class UUIDPrimaryKeyMixin:
    """Clave primaria UUID generada en aplicación y compatible con PostgreSQL/SQLite."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """Marcas temporales estándar de creación y actualización."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class SoftDeleteMixin:
    """Soporte de borrado lógico conservando historial referencial."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, default=None)
