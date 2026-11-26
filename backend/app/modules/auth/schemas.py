"""Esquemas Pydantic de autenticación, sesiones y perfil de usuario."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)
    birth_date: date | None = None
    preferred_ui_profile: Literal["kids", "youth", "pro"] = "pro"
    guardian_name: str | None = Field(default=None, max_length=160)
    guardian_email: EmailStr | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class MembershipSummary(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    sector_type: str
    default_ui_profile: str
    role_code: str
    role_name: str


class UserSummary(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_minor: bool
    preferred_ui_profile: str
    is_super_admin: bool
    created_at: datetime
    memberships: list[MembershipSummary] = Field(default_factory=list)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    csrf_token: str
    user: UserSummary
