"""Esquemas Pydantic para generación IA de lecciones, tutor socrático y proveedores."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.challenges.schemas import ChallengeType


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
