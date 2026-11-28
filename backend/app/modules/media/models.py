"""Modelos de recursos multimedia (S3/storage keys) y biblioteca visual personal."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class MediaAsset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Metadatos de archivo multimedia almacenado externamente (nunca blob en BD)."""

    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint(
            "education_level IN ('primary', 'secondary', 'high_school', 'university', 'technical', 'specialized', 'rescue')",
            name="ck_media_level",
        ),
        CheckConstraint("visibility IN ('public', 'institutional', 'private')", name="ck_media_visibility"),
        CheckConstraint(
            "media_format IN ('webp_anim', 'mp4_silent', 'webp', 'png', 'jpg', 'svg', 'pdf', 'audio_clip')",
            name="ck_media_format",
        ),
        CheckConstraint("processing_status IN ('pending', 'processing', 'ready', 'failed')", name="ck_media_status"),
        CheckConstraint("byte_size > 0", name="ck_media_size"),
        Index("idx_media_assets_org_status", "organization_id", "processing_status", "visibility"),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    competency_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("competencies.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags_json: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    education_level: Mapped[str] = mapped_column(String(40), nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), default="private", nullable=False)
    media_format: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    thumbnail_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_seconds: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    svg_markup: Mapped[str | None] = mapped_column(Text, nullable=True)
    dynamic_spec_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChallengeMediaAsset(Base):
    """Asociación M:N entre retos y recursos multimedia."""

    __tablename__ = "challenge_media_assets"
    __table_args__ = (
        CheckConstraint("role IN ('primary', 'option', 'diagram', 'explanation')", name="ck_cma_role"),
    )

    challenge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media_assets.id", ondelete="RESTRICT"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(30), default="primary", primary_key=True)
    order_index: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)


class StudentLibraryItem(Base, UUIDPrimaryKeyMixin):
    """Recurso desbloqueado en la biblioteca visual personal del estudiante."""

    __tablename__ = "student_library_items"
    __table_args__ = (
        CheckConstraint("flash_reviews_count >= 0", name="ck_sli_flash_count"),
        UniqueConstraint("user_id", "media_asset_id", name="uq_sli_user_asset"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False
    )
    unlocked_from_lesson_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lesson_versions.id", ondelete="SET NULL"), nullable=True
    )
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    flash_reviews_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
