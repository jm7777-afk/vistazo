"""Pruebas unitarias del algoritmo SM-2 adaptado y validación multimedia."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.core.exceptions import ValidationDomainError
from app.modules.media.service import sign_media_url, validate_media_upload, verify_media_signature
from app.modules.spaced_repetition.service import (
    SAFETY_CRITICAL_MAX_INTERVAL_DAYS,
    apply_sm2_step,
    compute_quality_score,
)


def test_sm2_progression_and_safety_critical_cap() -> None:
    now = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
    ef = Decimal("2.50")
    interval = 1
    reps = 0
    lapses = 0

    # Simula 7 aciertos perfectos seguidos en reto de seguridad crítica
    for _ in range(7):
        ef, interval, reps, lapses, state, next_at = apply_sm2_step(
            ease_factor=ef,
            interval_days=interval,
            repetitions=reps,
            lapses=lapses,
            quality=5,
            is_safety_critical=True,
            now=now,
        )
        assert interval <= SAFETY_CRITICAL_MAX_INTERVAL_DAYS
        assert state == "review"
        assert next_at > now

    # En reto normal, 6+ aciertos con intervalo >= 90 pasan a mastered
    ef_n, int_n, reps_n, lapses_n = Decimal("2.50"), 1, 0, 0
    state_n = "learning"
    for _ in range(6):
        ef_n, int_n, reps_n, lapses_n, state_n, _ = apply_sm2_step(
            ease_factor=ef_n,
            interval_days=int_n,
            repetitions=reps_n,
            lapses=lapses_n,
            quality=5,
            is_safety_critical=False,
            now=now,
        )
    assert int_n >= 90
    assert state_n == "mastered"


def test_sm2_failure_resets_to_relearning_and_quality_mapping() -> None:
    now = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
    q_fail = compute_quality_score(
        is_correct=False,
        attempt_number=2,
        hints_used=0,
        response_time_ms=4000,
        estimated_seconds=45,
    )
    assert q_fail == 1

    ef, interval, reps, lapses, state, next_at = apply_sm2_step(
        ease_factor=Decimal("2.50"),
        interval_days=12,
        repetitions=4,
        lapses=0,
        quality=q_fail,
        is_safety_critical=True,
        now=now,
    )
    assert reps == 0
    assert lapses == 1
    assert interval == 0
    assert state == "relearning"
    assert next_at == now + timedelta(minutes=10)
    assert ef < Decimal("2.50")


def test_media_validation_and_hmac_signed_urls() -> None:
    assert validate_media_upload("image/gif", 1024) == "webp_anim"
    assert validate_media_upload("video/mp4", 5_000_000) == "mp4_silent"

    with pytest.raises(ValidationDomainError):
        validate_media_upload("application/x-msdownload", 1024)
    with pytest.raises(ValidationDomainError):
        validate_media_upload("image/png", 30 * 1024 * 1024)

    asset_id = uuid.uuid4()
    url, exp = sign_media_url(asset_id, ttl_seconds=60)
    sig = url.split("sig=")[-1]
    assert verify_media_signature(asset_id, exp, sig) is True
    assert verify_media_signature(asset_id, exp, "tampered") is False
    assert verify_media_signature(asset_id, exp - 120, sig) is False
