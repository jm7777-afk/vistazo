"""Modelos curriculares: competencias, programas, pensums versionados y aulas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Competency(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Competencia evaluable global o institucional."""

    __tablename__ = "competencies"
    __table_args__ = (
        CheckConstraint(
            "education_level IN ('primary', 'secondary', 'high_school', 'university', 'technical', 'specialized', 'rescue')",
            name="ck_competency_level",
        ),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    education_level: Mapped[str] = mapped_column(String(40), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Program(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Programa formativo de una organización."""

    __tablename__ = "programs"
    __table_args__ = (
        CheckConstraint(
            "education_level IN ('primary', 'secondary', 'high_school', 'university', 'technical', 'specialized', 'rescue')",
            name="ck_program_level",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    education_level: Mapped[str] = mapped_column(String(40), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


Index(
    "uq_programs_org_code_active",
    Program.organization_id,
    func.lower(Program.code),
    unique=True,
    postgresql_where=text("deleted_at IS NULL"),
    sqlite_where=text("deleted_at IS NULL"),
)


class CurriculumVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Versión de pensum vinculada a un programa formativo."""

    __tablename__ = "curriculum_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="ck_cv_version_positive"),
        CheckConstraint("passing_score >= 0 AND passing_score <= 100", name="ck_cv_passing_score"),
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_cv_status"),
        UniqueConstraint("program_id", "version_number", name="uq_cv_program_version"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    passing_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("70.00"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)


class CurriculumUnit(Base, UUIDPrimaryKeyMixin):
    """Unidad del pensum vinculada a un curso y competencia principal."""

    __tablename__ = "curriculum_units"
    __table_args__ = (
        CheckConstraint("order_index >= 0", name="ck_cu_order_nonneg"),
        CheckConstraint("weight > 0", name="ck_cu_weight_pos"),
        UniqueConstraint("curriculum_version_id", "order_index", name="uq_cu_version_order"),
        UniqueConstraint("curriculum_version_id", "unit_code", name="uq_cu_version_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    curriculum_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("curriculum_versions.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )
    primary_competency_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("competencies.id", ondelete="SET NULL"), nullable=True
    )
    unit_code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("1.00"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Classroom(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Aula o cohorte institucional asociada a un pensum publicado."""

    __tablename__ = "classrooms"
    __table_args__ = (
        CheckConstraint("max_energy > 0 AND max_energy <= 20", name="ck_classroom_max_energy"),
        CheckConstraint("status IN ('planned', 'active', 'closed', 'archived')", name="ck_classroom_status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    curriculum_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("curriculum_versions.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    starts_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    energy_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_energy: Mapped[int] = mapped_column(SmallInteger, default=5, nullable=False)
    invite_code: Mapped[str | None] = mapped_column(String(24), unique=True, nullable=True)
    invite_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)


Index(
    "uq_classrooms_org_code_active",
    Classroom.organization_id,
    func.lower(Classroom.code),
    unique=True,
    postgresql_where=text("deleted_at IS NULL"),
    sqlite_where=text("deleted_at IS NULL"),
)


class ClassroomMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Matrícula de un estudiante dentro de un aula."""

    __tablename__ = "classroom_members"
    __table_args__ = (
        CheckConstraint("enrollment_status IN ('enrolled', 'completed', 'withdrawn')", name="ck_cm_status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    classroom_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    enrollment_status: Mapped[str] = mapped_column(String(20), default="enrolled", nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Index(
    "uq_classroom_members_active",
    ClassroomMember.classroom_id,
    ClassroomMember.user_id,
    unique=True,
    postgresql_where=text("deleted_at IS NULL"),
    sqlite_where=text("deleted_at IS NULL"),
)


class InstructorAssignment(Base, UUIDPrimaryKeyMixin):
    """Asignación explícita de instructor a un aula específica."""

    __tablename__ = "instructor_assignments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    classroom_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False
    )
    instructor_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    is_lead: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Index(
    "uq_instructor_assignment_active",
    InstructorAssignment.classroom_id,
    InstructorAssignment.instructor_user_id,
    unique=True,
    postgresql_where=text("deleted_at IS NULL"),
    sqlite_where=text("deleted_at IS NULL"),
)
