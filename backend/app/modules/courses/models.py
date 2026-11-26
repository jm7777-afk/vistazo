"""Modelos de cursos públicos/privados, módulos, lecciones y versiones inmutables."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Course(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Curso de estudio libre (public, org NULL) o institucional."""

    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint(
            "education_level IN ('primary', 'secondary', 'high_school', 'university', 'technical', 'specialized', 'rescue')",
            name="ck_course_level",
        ),
        CheckConstraint("ui_profile IN ('kids', 'youth', 'pro')", name="ck_course_ui_profile"),
        CheckConstraint("visibility IN ('public', 'institutional', 'private')", name="ck_course_visibility"),
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_course_status"),
        CheckConstraint(
            "(visibility = 'public' AND organization_id IS NULL) OR (visibility IN ('institutional', 'private') AND organization_id IS NOT NULL)",
            name="ck_course_scope_consistency",
        ),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    education_level: Mapped[str] = mapped_column(String(40), nullable=False)
    ui_profile: Mapped[str] = mapped_column(String(20), default="pro", nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), default="institutional", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)


Index(
    "uq_courses_public_slug_active",
    func.lower(Course.slug),
    unique=True,
    postgresql_where=text("organization_id IS NULL AND deleted_at IS NULL"),
    sqlite_where=text("organization_id IS NULL AND deleted_at IS NULL"),
)
Index(
    "uq_courses_org_slug_active",
    Course.organization_id,
    func.lower(Course.slug),
    unique=True,
    postgresql_where=text("organization_id IS NOT NULL AND deleted_at IS NULL"),
    sqlite_where=text("organization_id IS NOT NULL AND deleted_at IS NULL"),
)


class Module(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Módulo temático dentro de un curso."""

    __tablename__ = "modules"
    __table_args__ = (CheckConstraint("order_index >= 0", name="ck_module_order"),)

    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Lesson(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Lección lógica dentro de un módulo."""

    __tablename__ = "lessons"
    __table_args__ = (
        CheckConstraint("order_index >= 0", name="ck_lesson_order"),
        CheckConstraint("estimated_minutes > 0 AND estimated_minutes <= 120", name="ck_lesson_minutes"),
    )

    module_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(SmallInteger, default=5, nullable=False)
    is_safety_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LessonVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Versión inmutable publicada o en borrador de una lección."""

    __tablename__ = "lesson_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="ck_lv_version_pos"),
        CheckConstraint("status IN ('draft', 'published', 'superseded')", name="ck_lv_status"),
        UniqueConstraint("lesson_id", "version_number", name="uq_lesson_version_number"),
    )

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    requires_revalidation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
