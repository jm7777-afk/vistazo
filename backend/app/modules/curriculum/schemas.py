"""Esquemas Pydantic de competencias, programas, pensums y aulas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

EducationLevel = Literal[
    "primary",
    "secondary",
    "high_school",
    "university",
    "technical",
    "specialized",
    "rescue",
]


class CompetencyCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    education_level: EducationLevel


class CompetencyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    education_level: EducationLevel | None = None


class CompetencyOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    code: str
    title: str
    description: str | None
    education_level: str


class ProgramCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    education_level: EducationLevel


class ProgramUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    education_level: EducationLevel | None = None
    is_active: bool | None = None


class ProgramOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    title: str
    description: str | None
    education_level: str
    is_active: bool


class CurriculumVersionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    passing_score: Decimal = Field(default=Decimal("70.00"), ge=0, le=100)


class CurriculumVersionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    passing_score: Decimal | None = Field(default=None, ge=0, le=100)
    status: Literal["draft", "published", "archived"] | None = None


class CurriculumUnitCreate(BaseModel):
    course_id: uuid.UUID
    primary_competency_id: uuid.UUID | None = None
    unit_code: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=2, max_length=200)
    order_index: int = Field(ge=0)
    is_mandatory: bool = True
    weight: Decimal = Field(default=Decimal("1.00"), gt=0)


class CurriculumUnitOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    primary_competency_id: uuid.UUID | None
    unit_code: str
    title: str
    order_index: int
    is_mandatory: bool
    weight: Decimal


class CurriculumVersionOut(BaseModel):
    id: uuid.UUID
    program_id: uuid.UUID
    version_number: int
    title: str
    passing_score: Decimal
    status: str
    published_at: datetime | None
    units: list[CurriculumUnitOut] = Field(default_factory=list)


class ClassroomCreate(BaseModel):
    curriculum_version_id: uuid.UUID
    code: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=2, max_length=180)
    starts_at: date | None = None
    ends_at: date | None = None
    energy_enabled: bool = False
    max_energy: int = Field(default=5, ge=1, le=20)


class ClassroomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    energy_enabled: bool | None = None
    max_energy: int | None = Field(default=None, ge=1, le=20)
    status: Literal["planned", "active", "closed", "archived"] | None = None


class ClassroomOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    curriculum_version_id: uuid.UUID
    code: str
    name: str
    starts_at: date | None
    ends_at: date | None
    energy_enabled: bool
    max_energy: int
    invite_code: str | None = None
    invite_enabled: bool = True
    status: str


class JoinClassroomRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=24)


class InvitePreviewOut(BaseModel):
    classroom_id: uuid.UUID
    classroom_name: str
    classroom_code: str
    organization_id: uuid.UUID
    organization_name: str
    invite_code: str
    invite_enabled: bool


class JoinClassroomResponse(BaseModel):
    status: str
    organization_id: uuid.UUID
    classroom_id: uuid.UUID
    classroom_name: str


class EnrollStudentRequest(BaseModel):
    student_email: EmailStr


class AssignInstructorRequest(BaseModel):
    instructor_email: EmailStr
    is_lead: bool = False


class ClassroomStudentOut(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    enrollment_status: str
    enrolled_at: datetime
    completed_lessons: int
    avg_score_pct: float
