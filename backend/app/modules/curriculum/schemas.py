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
    status: str


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
