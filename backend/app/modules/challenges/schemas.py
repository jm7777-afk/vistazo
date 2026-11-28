"""Esquemas Pydantic de creación, edición y lectura segura de retos."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

ChallengeType = Literal[
    "visual_concept_card",
    "matching",
    "sequence_ordering",
    "interactive_zones",
    "decision_simulation",
    "fill_in_blanks",
    "open_response",
]


class ChallengeCreate(BaseModel):
    competency_id: uuid.UUID | None = None
    challenge_type: ChallengeType
    schema_version: int = Field(default=1, ge=1)
    order_index: int = Field(ge=0)
    prompt: str = Field(min_length=3, max_length=1000)
    payload_json: dict
    answer_key_json: dict
    pedagogical_explanation: str = Field(min_length=5, max_length=2000)
    difficulty: int = Field(default=2, ge=1, le=5)
    points: int = Field(default=10, ge=1, le=500)
    estimated_seconds: int = Field(default=45, ge=5, le=600)
    is_safety_critical: bool = False


class ChallengeUpdate(BaseModel):
    competency_id: uuid.UUID | None = None
    order_index: int | None = Field(default=None, ge=0)
    prompt: str | None = Field(default=None, min_length=3, max_length=1000)
    payload_json: dict | None = None
    answer_key_json: dict | None = None
    pedagogical_explanation: str | None = Field(default=None, min_length=5, max_length=2000)
    difficulty: int | None = Field(default=None, ge=1, le=5)
    points: int | None = Field(default=None, ge=1, le=500)
    estimated_seconds: int | None = Field(default=None, ge=5, le=600)
    is_safety_critical: bool | None = None
    status: Literal["draft", "published", "archived"] | None = None


class ChallengePublicOut(BaseModel):
    """DTO seguro para el estudiante: nunca expone answer_key_json."""

    id: uuid.UUID
    lesson_version_id: uuid.UUID
    competency_id: uuid.UUID | None
    challenge_type: str
    schema_version: int
    order_index: int
    prompt: str
    payload_json: dict
    difficulty: int
    points: int
    estimated_seconds: int
    is_safety_critical: bool
    status: str


class ChallengeAuthorOut(ChallengePublicOut):
    """DTO para autores/instructores dentro de su organización."""

    answer_key_json: dict
    pedagogical_explanation: str


class QuestionBankCreate(BaseModel):
    competency_id: uuid.UUID | None = None
    topic_tag: str = Field(default="general", min_length=1, max_length=80)
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


class QuestionBankUpdate(BaseModel):
    topic_tag: str | None = Field(default=None, min_length=1, max_length=80)
    prompt: str | None = Field(default=None, min_length=3, max_length=1000)
    pedagogical_explanation: str | None = Field(default=None, min_length=5, max_length=2000)
    difficulty: int | None = Field(default=None, ge=1, le=5)
    points: int | None = Field(default=None, ge=1, le=500)


class QuestionBankOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    competency_id: uuid.UUID | None
    topic_tag: str
    challenge_type: str
    prompt: str
    payload_json: dict
    answer_key_json: dict
    pedagogical_explanation: str
    difficulty: int
    points: int
    is_safety_critical: bool


class PullFromBankRequest(BaseModel):
    count: int = Field(default=5, ge=1, le=30)
    topic_tag: str | None = None
    competency_id: uuid.UUID | None = None


class OpenSubmissionOut(BaseModel):
    id: uuid.UUID
    challenge_id: uuid.UUID
    user_id: uuid.UUID
    response_text: str
    attachment_note: str | None
    max_points: int
    ai_suggested_score: int
    ai_feedback: str | None
    final_score: int | None
    teacher_feedback: str | None
    status: str


class GradeOpenSubmissionRequest(BaseModel):
    final_score: int = Field(ge=0, le=500)
    teacher_feedback: str = Field(min_length=2, max_length=2000)
