"""Pruebas unitarias de hashing, generación PDF+QR, máscara PII y anti-enumeración."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.core.exceptions import AppError
from app.modules.certificates.service import (
    check_verify_rate_limit,
    compute_signature_hash,
    compute_verification_hash,
    generate_certificate_pdf_bytes,
    mask_recipient_name,
    reset_verify_rate_limiter,
)


def test_verification_hash_uniqueness_and_pii_masking() -> None:
    now = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
    cid = uuid.uuid4()
    oid = uuid.uuid4()
    uid = uuid.uuid4()
    cvid = uuid.uuid4()

    h1 = compute_verification_hash(
        certificate_id=cid, organization_id=oid, user_id=uid, curriculum_version_id=cvid, issued_at=now
    )
    h2 = compute_verification_hash(
        certificate_id=cid, organization_id=oid, user_id=uid, curriculum_version_id=cvid, issued_at=now
    )
    assert len(h1) == 64
    assert h1 != h2
    assert mask_recipient_name("Cadete Lucía Méndez") == "C. L. M."

    sig = compute_signature_hash(
        certificate_number="BRIGADA-2026-ABCDEF",
        verification_hash=h1,
        final_grade=Decimal("95.00"),
        signer_user_id=uid,
    )
    assert len(sig) == 64


def test_pdf_with_qr_generation() -> None:
    pdf_bytes = generate_certificate_pdf_bytes(
        organization_name="Brigada de Rescate Alfa",
        recipient_name="Cadete Lucía Méndez",
        program_title="Formación Inicial de Brigadista",
        curriculum_title="Pensum 2026 v1",
        certificate_number="BRIGADA-2026-001",
        verification_hash="a" * 64,
        final_grade=Decimal("100.00"),
        issued_at=datetime.now(timezone.utc),
        signer_name="Comandante Elena Rojas",
        signer_title="Coordinación",
        verification_url="https://vistazo.org/verificar-certificado/" + ("a" * 64),
    )
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_anti_enumeration_rate_limit() -> None:
    reset_verify_rate_limiter()
    for _ in range(30):
        check_verify_rate_limit("203.0.113.10", max_requests=30, window_seconds=60)
    with pytest.raises(AppError) as exc_info:
        check_verify_rate_limit("203.0.113.10", max_requests=30, window_seconds=60)
    assert exc_info.value.status_code == 429
    reset_verify_rate_limiter()
