"""Esquemas Pydantic de emisión, revocación y verificación pública de certificados."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class IssueCertificateRequest(BaseModel):
    student_email: EmailStr
    curriculum_version_id: uuid.UUID
    classroom_id: uuid.UUID | None = None
    signer_title: str = Field(default="Coordinación Académica", min_length=2, max_length=160)


class RevokeCertificateRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class CertificateOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    curriculum_version_id: uuid.UUID
    classroom_id: uuid.UUID | None
    certificate_number: str
    verification_hash: str
    final_grade: Decimal
    status: str
    issued_at: datetime | None
    verification_url: str
    has_pdf: bool


class PublicCertificateVerificationOut(BaseModel):
    """Respuesta pública mínima sin PII sensible del estudiante."""

    valid: bool
    status: str
    certificate_number: str
    organization_name: str
    program_title: str
    curriculum_title: str
    recipient_initials: str
    final_grade: Decimal
    issued_at: datetime | None
    signer_name: str
    signer_title: str
    revoked_at: datetime | None = None
    revocation_reason: str | None = None
