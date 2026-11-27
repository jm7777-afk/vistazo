"""Esquemas Pydantic de cursos, módulos, lecciones, versiones y guías de estudio."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.curriculum.schemas import EducationLevel

LessonType = Literal["micro_lesson", "strong_exam", "study_guide_drill"]
GuideType = Literal["pensum", "temario", "guia_estudio", "metodologia", "rubrica"]


class CourseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    education_level: EducationLevel
    ui_profile: Literal["kids", "youth", "pro"] = "pro"
    visibility: Literal["institutional", "private", "public"] = "institutional"


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    education_level: EducationLevel | None = None
    ui_profile: Literal["kids", "youth", "pro"] | None = None
    visibility: Literal["institutional", "private", "public"] | None = None
    status: Literal["draft", "published", "archived"] | None = None


class ModuleCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    order_index: int = Field(ge=0)


class ModuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    order_index: int | None = Field(default=None, ge=0)


class LessonCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9-]+$")
    order_index: int = Field(ge=0)
    estimated_minutes: int = Field(default=5, ge=1, le=120)
    lesson_type: LessonType = "micro_lesson"
    passing_score_pct: int = Field(default=70, ge=0, le=100)
    is_safety_critical: bool = False


class LessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    order_index: int | None = Field(default=None, ge=0)
    estimated_minutes: int | None = Field(default=None, ge=1, le=120)
    lesson_type: LessonType | None = None
    passing_score_pct: int | None = Field(default=None, ge=0, le=100)
    is_safety_critical: bool | None = None


class LessonVersionCreate(BaseModel):
    summary: str | None = None
    requires_revalidation: bool = False


class LessonOut(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    order_index: int
    estimated_minutes: int
    lesson_type: str = "micro_lesson"
    passing_score_pct: int = 70
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


class StudyGuideCreate(BaseModel):
    course_id: uuid.UUID | None = None
    lesson_id: uuid.UUID | None = None
    guide_type: GuideType = "guia_estudio"
    title: str = Field(min_length=2, max_length=200)
    content_markdown: str = Field(min_length=10, max_length=30000)
    methodology_json: dict = Field(default_factory=dict)
    status: Literal["draft", "published"] = "draft"


class StudyGuideUpdate(BaseModel):
    guide_type: GuideType | None = None
    title: str | None = Field(default=None, min_length=2, max_length=200)
    content_markdown: str | None = Field(default=None, min_length=10, max_length=30000)
    methodology_json: dict | None = None
    status: Literal["draft", "published", "archived"] | None = None


class StudyGuideOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    course_id: uuid.UUID | None
    lesson_id: uuid.UUID | None
    guide_type: str
    title: str
    content_markdown: str
    methodology_json: dict
    status: str
    ai_generated: bool
    created_at: datetime
    updated_at: datetime
