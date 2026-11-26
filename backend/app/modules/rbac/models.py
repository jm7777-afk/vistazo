"""Modelos RBAC: roles, permisos y relación rol-permiso."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Rol de sistema (organization_id NULL) o personalizado por organización."""

    __tablename__ = "roles"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Index(
    "uq_roles_global_code_active",
    func.lower(Role.code),
    unique=True,
    postgresql_where=text("organization_id IS NULL AND deleted_at IS NULL"),
    sqlite_where=text("organization_id IS NULL AND deleted_at IS NULL"),
)
Index(
    "uq_roles_org_code_active",
    Role.organization_id,
    func.lower(Role.code),
    unique=True,
    postgresql_where=text("organization_id IS NOT NULL AND deleted_at IS NULL"),
    sqlite_where=text("organization_id IS NOT NULL AND deleted_at IS NULL"),
)


class Permission(Base, UUIDPrimaryKeyMixin):
    """Permiso granular sobre recurso y acción."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(60), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RolePermission(Base):
    """Asociación M:N entre roles y permisos."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
