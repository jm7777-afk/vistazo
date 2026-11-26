"""Modelos de organizaciones (tenants) y membresías institucionales."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONType, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Entidad tenant que aísla programas, aulas, pensums y estudiantes."""

    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "sector_type IN ('primary_school', 'secondary_school', 'high_school', 'university', 'technical_academy', 'rescue_brigade', 'specialized_training')",
            name="ck_org_sector_type",
        ),
        CheckConstraint("default_ui_profile IN ('kids', 'youth', 'pro')", name="ck_org_ui_profile"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    sector_type: Mapped[str] = mapped_column(String(40), nullable=False)
    default_ui_profile: Mapped[str] = mapped_column(String(20), default="pro", nullable=False)
    settings_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


Index(
    "uq_organizations_slug_active",
    func.lower(Organization.slug),
    unique=True,
    postgresql_where=text("deleted_at IS NULL"),
    sqlite_where=text("deleted_at IS NULL"),
)


class OrganizationMember(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Membresía de un usuario dentro de una organización con un rol específico."""

    __tablename__ = "organization_members"
    __table_args__ = (
        CheckConstraint("status IN ('invited', 'active', 'suspended')", name="ck_org_member_status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


Index(
    "uq_org_member_role_active",
    OrganizationMember.organization_id,
    OrganizationMember.user_id,
    OrganizationMember.role_id,
    unique=True,
    postgresql_where=text("deleted_at IS NULL"),
    sqlite_where=text("deleted_at IS NULL"),
)
Index(
    "idx_org_members_user_org",
    OrganizationMember.user_id,
    OrganizationMember.organization_id,
    postgresql_where=text("deleted_at IS NULL"),
    sqlite_where=text("deleted_at IS NULL"),
)
