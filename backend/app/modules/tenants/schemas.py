"""Esquemas Pydantic para gestión de organizaciones y miembros."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

SectorType = Literal[
    "primary_school",
    "secondary_school",
    "high_school",
    "university",
    "technical_academy",
    "rescue_brigade",
    "specialized_training",
]
UIProfileType = Literal["kids", "youth", "pro"]


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    sector_type: SectorType
    default_ui_profile: UIProfileType = "pro"
    settings_json: dict = Field(default_factory=dict)


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    sector_type: str
    default_ui_profile: str
    is_active: bool
    created_at: datetime


class AddMemberRequest(BaseModel):
    user_email: EmailStr
    role_code: Literal["coordinator", "instructor", "student"]


class OrganizationMemberOut(BaseModel):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role_code: str
    role_name: str
    status: str
    joined_at: datetime


class AuditLogOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: uuid.UUID | None
    outcome: str
    details_json: dict
    created_at: datetime
