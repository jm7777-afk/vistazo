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
