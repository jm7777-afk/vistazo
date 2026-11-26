"""Modelos de certificación institucional verificable, firma y revocación."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Certificate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Certificado emitido por una organización con hash criptográfico único."""

    __tablename__ = "certificates"
    __table_args__ = (
        CheckConstraint("final_grade >= 0 AND final_grade <= 100", name="ck_cert_grade"),
        CheckConstraint("status IN ('pending', 'issued', 'revoked')", name="ck_cert_status"),
        Index("idx_certificates_org_user", "organization_id", "user_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    curriculum_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("curriculum_versions.id", ondelete="RESTRICT"), nullable=False
    )
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("classrooms.id", ondelete="SET NULL"), nullable=True
    )
    certificate_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    verification_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    final_grade: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    pdf_storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_snapshot_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CertificateSignature(Base, UUIDPrimaryKeyMixin):
    """Firma autorizada criptográfica asociada al certificado."""

    __tablename__ = "certificate_signatures"

    certificate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("certificates.id", ondelete="CASCADE"), nullable=False
    )
    signer_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    signer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    signer_title: Mapped[str] = mapped_column(String(160), nullable=False)
    signature_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CertificateRevocation(Base, UUIDPrimaryKeyMixin):
    """Registro inmutable de revocación de certificado."""

    __tablename__ = "certificate_revocations"

    certificate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("certificates.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    revoked_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
