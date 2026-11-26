"""Esquemas Pydantic de cursos, módulos, lecciones y versiones."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.curriculum.schemas import EducationLevel


class CourseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    education_level: EducationLevel
    ui_profile: Literal["kids", "youth", "pro"] = "pro"
    visibility: Literal["institutional", "private"] = "institutional"


class ModuleCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    order_index: int = Field(ge=0)


class LessonCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9-]+$")
    order_index: int = Field(ge=0)
    estimated_minutes: int = Field(default=5, ge=1, le=120)
    is_safety_critical: bool = False


class LessonVersionCreate(BaseModel):
    summary: str | None = None
    requires_revalidation: bool = False


class LessonOut(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    order_index: int
    estimated_minutes: int
    is_safety_critical: bool
    active_lesson_version_id: uuid.UUID | None = None
    active_version_number: int | None = None


class ModuleOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    order_index: int
    lessons: list[LessonOut] = Field(default_factory=list)


class CourseSummaryOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    title: str
    slug: str
    description: str | None
    education_level: str
    ui_profile: str
    visibility: str
    status: str


class CourseDetailOut(CourseSummaryOut):
    modules: list[ModuleOut] = Field(default_factory=list)


class LessonVersionOut(BaseModel):
    id: uuid.UUID
    lesson_id: uuid.UUID
    version_number: int
    summary: str | None
    status: str
    requires_revalidation: bool
    published_at: datetime | None
