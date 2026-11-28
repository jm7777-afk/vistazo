"""Esquemas Pydantic para generación IA de lecciones, blueprints, guías, exámenes fuertes e imágenes dinámicas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.challenges.schemas import ChallengeType
from app.modules.courses.schemas import GuideType, LessonType
from app.modules.curriculum.schemas import EducationLevel

PedagogyStyle = Literal["active_recall", "problem_based", "flipped_mastery", "spaced_microlearning"]
DiagramKind = Literal["auto", "cycle", "flowchart", "hierarchy", "comparison", "layers"]


class GeneratedChallengeDraft(BaseModel):
    challenge_type: ChallengeType
    schema_version: int = Field(default=1, ge=1)
    prompt: str = Field(min_length=3, max_length=1000)
    payload_json: dict
    answer_key_json: dict
    pedagogical_explanation: str = Field(min_length=5, max_length=2000)
    difficulty: int = Field(default=2, ge=1, le=5)
    points: int = Field(default=10, ge=1, le=500)
    estimated_seconds: int = Field(default=45, ge=5, le=600)
    is_safety_critical: bool = False


class LessonDraftPayload(BaseModel):
    lesson_summary: str = Field(min_length=5, max_length=300)
    challenges: list[GeneratedChallengeDraft] = Field(min_length=5, max_length=8)


class GenerateLessonDraftRequest(BaseModel):
    lesson_version_id: uuid.UUID
    competency_id: uuid.UUID | None = None
    source_text: str = Field(min_length=20, max_length=10000)


class GenerateLessonDraftResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    job_id: uuid.UUID
    provider: str
    model_name: str
    status: str
    used_fallback: bool
    lesson_summary: str
    challenges_created: int
    challenge_ids: list[uuid.UUID]


class BlueprintLessonDraft(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    lesson_type: LessonType = "micro_lesson"
    estimated_minutes: int = Field(default=6, ge=1, le=120)
    passing_score_pct: int = Field(default=75, ge=0, le=100)
    is_safety_critical: bool = False
    key_concepts: list[str] = Field(default_factory=list)


class BlueprintModuleDraft(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = ""
    lessons: list[BlueprintLessonDraft] = Field(min_length=1, max_length=8)


class BlueprintPayload(BaseModel):
    course_title: str = Field(min_length=3, max_length=200)
    course_description: str = Field(min_length=10, max_length=1200)
    methodology: dict
    study_guide_markdown: str = Field(min_length=30, max_length=30000)
    modules: list[BlueprintModuleDraft] = Field(min_length=2, max_length=6)


class GenerateBlueprintRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=200)
    education_level: EducationLevel = "specialized"
    ui_profile: Literal["kids", "youth", "pro"] = "pro"
    pedagogy_style: PedagogyStyle = "active_recall"
    source_text: str = Field(default="", max_length=10000)
    modules_count: int = Field(default=3, ge=2, le=5)
    save_to_course: bool = False
    target_course_id: uuid.UUID | None = None


class GenerateBlueprintResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    job_id: uuid.UUID
    provider: str
    model_name: str
    status: str
    used_fallback: bool
    blueprint: BlueprintPayload
    created_course_id: uuid.UUID | None = None
    created_guide_id: uuid.UUID | None = None


class GenerateStudyGuideRequest(BaseModel):
    course_id: uuid.UUID | None = None
    lesson_id: uuid.UUID | None = None
    guide_type: GuideType = "guia_estudio"
    topic: str = Field(min_length=3, max_length=200)
    source_text: str = Field(default="", max_length=10000)
    pedagogy_style: PedagogyStyle = "active_recall"
    education_level: EducationLevel = "specialized"
    save_as_draft: bool = True


class StudyGuideDraftPayload(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    content_markdown: str = Field(min_length=30, max_length=30000)
    methodology_json: dict = Field(default_factory=dict)


class GenerateStudyGuideResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    job_id: uuid.UUID
    provider: str
    model_name: str
    status: str
    used_fallback: bool
    title: str
    content_markdown: str
    methodology_json: dict
    saved_guide_id: uuid.UUID | None = None


class GenerateStrongExamRequest(BaseModel):
    lesson_version_id: uuid.UUID
    competency_id: uuid.UUID | None = None
    source_text: str = Field(min_length=40, max_length=10000)
    difficulty_target: int = Field(default=4, ge=3, le=5)
    question_count: int = Field(default=6, ge=5, le=8)
    focus_notes: str | None = Field(default=None, max_length=500)


class GenerateDynamicVisualRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=200)
    diagram_kind: DiagramKind = "auto"
    context_text: str = Field(default="", max_length=6000)
    education_level: EducationLevel = "specialized"
    lesson_version_id: uuid.UUID | None = None
    create_interactive_challenge: bool = False


class DynamicVisualPayload(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    subtitle: str = Field(default="Infografía dinámica de aprendizaje", max_length=160)
    template: Literal["cycle", "flowchart", "hierarchy", "comparison", "layers"]
    nodes: list[dict] = Field(min_length=2, max_length=6)
    recommended_question: str = Field(min_length=5, max_length=400)
    correct_node_id: str = Field(min_length=1, max_length=32)
    explanation: str = Field(min_length=5, max_length=1000)


class GenerateDynamicVisualResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    job_id: uuid.UUID
    provider: str
    model_name: str
    status: str
    used_fallback: bool
    media_asset_id: uuid.UUID
    signed_url: str
    title: str
    template: str
    zones: list[dict]
    created_challenge_id: uuid.UUID | None = None


class SocraticHintRequest(BaseModel):
    student_question: str | None = Field(default=None, max_length=500)


class SocraticHintResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    job_id: uuid.UUID
    hint: str
    provider: str
    model_name: str
    used_fallback: bool
    failed_attempts: int
    safety_reminder: bool


class AIProviderConfigOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: uuid.UUID
    provider: str
    model_name: str
    is_active: bool
    max_tokens: int
    daily_org_job_limit: int
    has_api_key_configured: bool


class AIProviderUpdateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider: Literal["gemini", "groq", "fallback"]
    model_name: str = Field(min_length=2, max_length=80)
    max_tokens: int = Field(default=2500, ge=256, le=8192)
    daily_org_job_limit: int = Field(default=50, ge=1, le=5000)


class AIJobOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: uuid.UUID
    organization_id: uuid.UUID | None
    job_type: str
    provider: str
    model_name: str
    status: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int | None
    error_code: str | None
    created_at: datetime


class DocumentExtractResponse(BaseModel):
    filename: str
    char_count: int
    extracted_text: str


class AdaptiveRemediationRequest(BaseModel):
    course_id: uuid.UUID | None = None
    missed_prompts: list[str] = Field(min_length=1, max_length=12)


class AdaptiveRemediationResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    job_id: uuid.UUID
    provider: str
    title: str
    remediation_markdown: str
    action_steps: list[str]
