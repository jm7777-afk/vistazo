"""Modelos de identidad, sesiones de refresh token y consentimiento parental."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, SmallInteger, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Identidad global del usuario en la plataforma."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("preferred_ui_profile IN ('kids', 'youth', 'pro')", name="ck_users_ui_profile"),
        CheckConstraint("account_type IN ('student', 'educator')", name="ck_users_account_type"),
        CheckConstraint("daily_goal_minutes BETWEEN 3 AND 120", name="ck_users_daily_goal"),
        Index(
            "uq_users_email_active",
            func.lower("email"),  # fallback overridden below if needed
            unique=True,
        ),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), default="student", nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_minor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    preferred_ui_profile: Mapped[str] = mapped_column(String(20), default="pro", nullable=False)
    daily_goal_minutes: Mapped[int] = mapped_column(SmallInteger, default=5, nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    family_access_code: Mapped[str | None] = mapped_column(String(24), unique=True, nullable=True)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# Reemplaza índice funcional limpio sobre columna real
User.__table__.indexes.clear()
Index(
    "uq_users_email_active",
    func.lower(User.email),
    unique=True,
    postgresql_where=text("deleted_at IS NULL"),
    sqlite_where=text("deleted_at IS NULL"),
)


class UserSession(Base, UUIDPrimaryKeyMixin):
    """Sesiones de refresh token opaco rotativo por familia."""

    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ParentalConsent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Registro de consentimiento verificable para cuentas de menores."""

    __tablename__ = "parental_consents"
    __table_args__ = (
        CheckConstraint("consent_status IN ('pending', 'verified', 'revoked')", name="ck_parental_consent_status"),
    )

    minor_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    guardian_name: Mapped[str] = mapped_column(String(160), nullable=False)
    guardian_email: Mapped[str] = mapped_column(String(320), nullable=False)
    consent_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    verification_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordResetToken(Base, UUIDPrimaryKeyMixin):
    """Tokens opacos temporales para recuperación de contraseña."""

    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EmailVerificationToken(Base, UUIDPrimaryKeyMixin):
    """Tokens opacos para verificación de correo electrónico."""

    __tablename__ = "email_verification_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
