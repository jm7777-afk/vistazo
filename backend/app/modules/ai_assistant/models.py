"""Modelos de trazabilidad de consumo IA y configuración de proveedores."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class AIProviderConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Configuración activa de proveedor IA (sin almacenar API keys en BD)."""

    __tablename__ = "ai_provider_configs"
    __table_args__ = (
        CheckConstraint("provider IN ('gemini', 'groq', 'fallback')", name="ck_ai_provider_name"),
        CheckConstraint("max_tokens > 0", name="ck_ai_provider_max_tokens"),
        CheckConstraint("daily_org_job_limit > 0", name="ck_ai_provider_daily_limit"),
    )

    provider: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2500, nullable=False)
    daily_org_job_limit: Mapped[int] = mapped_column(Integer, default=50, nullable=False)


class AIGenerationJob(Base, UUIDPrimaryKeyMixin):
    """Registro append-only de solicitudes, tokens, latencia y fallbacks de IA."""

    __tablename__ = "ai_generation_jobs"
    __table_args__ = (
        CheckConstraint(
            "job_type IN ('lesson_generator', 'socratic_tutor', 'blueprint_architect', 'study_guide', 'strong_exam', 'dynamic_visual', 'adaptive_remediation')",
            name="ck_ai_job_type",
        ),
        CheckConstraint("status IN ('pending', 'completed', 'failed', 'fallback_used')", name="ck_ai_job_status"),
        CheckConstraint("prompt_tokens >= 0", name="ck_ai_prompt_tokens"),
        CheckConstraint("completion_tokens >= 0", name="ck_ai_completion_tokens"),
        Index("idx_ai_jobs_org_date", "organization_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(String(30), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    target_lesson_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lesson_versions.id", ondelete="SET NULL"), nullable=True
    )
    target_challenge_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("challenges.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AsyncTaskRecord(Base, UUIDPrimaryKeyMixin):
    """Registro de trabajos pesados en segundo plano (generación masiva, exportaciones)."""

    __tablename__ = "async_task_records"
    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name="ck_async_task_status"),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    task_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
