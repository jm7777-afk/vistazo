"""Servicios de negocio para Generador de Lecciones IA y Tutor Socrático."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from fastapi import status as http_status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError, ForbiddenError, NotFoundError, ValidationDomainError
from app.modules.ai_assistant.guardrails import (
    extract_json_object,
    sanitize_socratic_output,
    strip_unsafe_markup,
    validate_and_sanitize_source_text,
    validate_student_question,
)
from app.modules.ai_assistant.models import AIGenerationJob, AIProviderConfig
from app.modules.ai_assistant.prompts import (
    LESSON_GENERATOR_SYSTEM_PROMPT,
    SOCRATIC_TUTOR_SYSTEM_PROMPT,
    build_lesson_generator_user_prompt,
    build_socratic_user_prompt,
)
from app.modules.ai_assistant.providers import run_with_fallback
from app.modules.ai_assistant.schemas import (
    GenerateLessonDraftResponse,
    LessonDraftPayload,
    SocraticHintResponse,
)
from app.modules.audit.service import record_audit_log
from app.modules.auth.models import User
from app.modules.challenges.evaluators import get_challenge_handler
from app.modules.challenges.models import Challenge
from app.modules.courses.models import Course, Lesson, LessonVersion, Module
from app.modules.curriculum.models import Competency
from app.modules.progress.models import ChallengeAttempt
from app.modules.tenants.models import OrganizationMember


def get_active_provider_config(db: Session) -> tuple[str, str, int, int]:
    """Obtiene proveedor activo desde BD o valores por defecto de configuración."""
    settings = get_settings()
    active = db.scalar(select(AIProviderConfig).where(AIProviderConfig.is_active.is_(True)))
    if active:
        return active.provider, active.model_name, active.max_tokens, active.daily_org_job_limit
    model_default = (
        settings.gemini_model
        if settings.ai_provider == "gemini"
        else settings.groq_model
        if settings.ai_provider == "groq"
        else "deterministic-pedagogical-v1"
    )
    return settings.ai_provider, model_default, settings.ai_max_tokens, settings.ai_daily_org_job_limit


def _enforce_daily_quota(db: Session, organization_id: uuid.UUID | None, daily_limit: int) -> None:
    if organization_id is None:
        return
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    used_today = db.scalar(
        select(func.count(AIGenerationJob.id)).where(
            AIGenerationJob.organization_id == organization_id,
            AIGenerationJob.created_at >= start_of_day,
        )
    ) or 0
    if int(used_today) >= daily_limit:
        raise AppError(
            code="ai_quota_exceeded",
            message="Cuota diaria de generación IA alcanzada para esta organización",
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
        )


def generate_lesson_draft_challenges(
    db: Session,
    *,
    organization_id: uuid.UUID,
    user: User,
    lesson_version_id: uuid.UUID,
    competency_id: uuid.UUID | None,
    source_text: str,
) -> GenerateLessonDraftResponse:
    row = db.execute(
        select(LessonVersion, Lesson, Course)
        .join(Lesson, LessonVersion.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            LessonVersion.id == lesson_version_id,
            Course.organization_id == organization_id,
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Versión de lección no encontrada en esta organización")

    lv, _lesson, course = row
    if lv.status != "draft":
        raise ValidationDomainError("Solo se pueden generar retos IA en versiones en estado borrador")

    clean_source = validate_and_sanitize_source_text(source_text)
    provider_name, model_name, max_tokens, daily_limit = get_active_provider_config(db)
    _enforce_daily_quota(db, organization_id, daily_limit)

    competency_title = "Competencia general del módulo"
    if competency_id:
        comp = db.scalar(
            select(Competency).where(
                Competency.id == competency_id,
                Competency.deleted_at.is_(None),
                (Competency.organization_id == organization_id) | (Competency.organization_id.is_(None)),
            )
        )
        if not comp:
            raise NotFoundError("Competencia no válida para esta organización")
        competency_title = f"{comp.code}: {comp.title}"

    user_prompt = build_lesson_generator_user_prompt(
        source_text=clean_source,
        education_level=course.education_level,
        ui_profile=course.ui_profile,
        competency_title=competency_title,
    )

    settings = get_settings()
    t0 = time.monotonic()
    llm_res = run_with_fallback(
        provider_name=provider_name,
        model_name=model_name,
        system_prompt=LESSON_GENERATOR_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        timeout_seconds=settings.ai_timeout_seconds,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    job = AIGenerationJob(
        organization_id=organization_id,
        requested_by=user.id,
        job_type="lesson_generator",
        provider=llm_res.provider,
        model_name=llm_res.model_name,
        target_lesson_version_id=lv.id,
        status="fallback_used" if llm_res.used_fallback else "completed",
        prompt_tokens=llm_res.prompt_tokens,
        completion_tokens=llm_res.completion_tokens,
        latency_ms=latency_ms,
        error_code=llm_res.fallback_reason,
        completed_at=datetime.now(timezone.utc),
    )

    try:
        raw_json = extract_json_object(llm_res.text)
        if "error" in raw_json:
            raise ValidationDomainError(str(raw_json["error"]), code="insufficient_source_content")
        draft_payload = LessonDraftPayload.model_validate(raw_json)
    except (ValidationError, ValidationDomainError) as exc:
        job.status = "failed"
        job.error_code = "invalid_ai_schema"
        db.add(job)
        db.commit()
        raise ValidationDomainError(f"La salida de IA no cumplió el contrato de retos: {exc}") from exc

    # Valida cada reto contra el Registry Pydantic antes de persistir
    max_order = db.scalar(
        select(func.coalesce(func.max(Challenge.order_index), 0)).where(
            Challenge.lesson_version_id == lv.id,
            Challenge.deleted_at.is_(None),
        )
    )
    next_order = int(max_order or 0) + 1
    created_ids: list[uuid.UUID] = []

    for item in draft_payload.challenges:
        handler = get_challenge_handler(item.challenge_type, item.schema_version)
        clean_p, clean_k = handler.validate_definition(item.payload_json, item.answer_key_json)
        ch = Challenge(
            lesson_version_id=lv.id,
            competency_id=competency_id,
            challenge_type=item.challenge_type,
            schema_version=item.schema_version,
            order_index=next_order,
            prompt=strip_unsafe_markup(item.prompt),
            payload_json=clean_p,
            answer_key_json=clean_k,
            pedagogical_explanation=strip_unsafe_markup(item.pedagogical_explanation),
            difficulty=item.difficulty,
            points=item.points,
            estimated_seconds=item.estimated_seconds,
            is_safety_critical=item.is_safety_critical,
            status="draft",
            ai_generated=True,
        )
        db.add(ch)
        db.flush()
        created_ids.append(ch.id)
        next_order += 1

    lv.summary = strip_unsafe_markup(draft_payload.lesson_summary)
    db.add(job)
    record_audit_log(
        db,
        action="ai.lesson_draft_generated",
        resource_type="lesson_version",
        resource_id=lv.id,
        organization_id=organization_id,
        actor_user_id=user.id,
        details={"challenges_created": len(created_ids), "provider": llm_res.provider},
    )
    db.commit()
    return GenerateLessonDraftResponse(
        job_id=job.id,
        provider=llm_res.provider,
        model_name=llm_res.model_name,
        status=job.status,
        used_fallback=llm_res.used_fallback,
        lesson_summary=lv.summary,
        challenges_created=len(created_ids),
        challenge_ids=created_ids,
    )


def _extract_forbidden_answer_tokens(challenge: Challenge) -> list[str]:
    tokens: list[str] = []
    ak = challenge.answer_key_json
    if "correct_option_id" in ak:
        opt_id = ak["correct_option_id"]
        for opt in challenge.payload_json.get("check_question", {}).get("options", []):
            if opt.get("id") == opt_id:
                tokens.append(str(opt.get("text", "")))
    if "blanks" in ak:
        for rule in ak["blanks"].values():
            for accepted in rule.get("accepted", []):
                tokens.append(str(accepted))
    return tokens


def generate_socratic_hint(
    db: Session,
    *,
    user: User,
    challenge_id: uuid.UUID,
    student_question: str | None,
) -> SocraticHintResponse:
    row = db.execute(
        select(Challenge, Course)
        .join(LessonVersion, Challenge.lesson_version_id == LessonVersion.id)
        .join(Lesson, LessonVersion.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(Challenge.id == challenge_id, Challenge.deleted_at.is_(None), Course.deleted_at.is_(None))
    ).first()
    if not row:
        raise NotFoundError("Reto no encontrado")

    ch, course = row
    if course.visibility != "public" and not user.is_super_admin:
        member = db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == course.organization_id,
                OrganizationMember.user_id == user.id,
                OrganizationMember.deleted_at.is_(None),
                OrganizationMember.status == "active",
            )
        )
        if not member:
            raise ForbiddenError("No perteneces a la organización de este reto")

    failed_attempts = db.scalar(
        select(func.count(ChallengeAttempt.id)).where(
            ChallengeAttempt.user_id == user.id,
            ChallengeAttempt.challenge_id == ch.id,
            ChallengeAttempt.is_correct.is_(False),
        )
    ) or 0
    if int(failed_attempts) < 2:
        raise ValidationDomainError(
            "El Tutor Socrático se habilita después de al menos 2 intentos fallidos en este reto",
            code="socratic_requires_two_failures",
        )

    clean_q = validate_student_question(student_question)
    provider_name, model_name, max_tokens, daily_limit = get_active_provider_config(db)
    _enforce_daily_quota(db, course.organization_id, daily_limit)

    user_prompt = build_socratic_user_prompt(
        education_level=course.education_level,
        ui_profile=course.ui_profile,
        is_safety_critical=ch.is_safety_critical,
        challenge_prompt=ch.prompt,
        authorized_explanation=ch.pedagogical_explanation,
        attempt_count=int(failed_attempts),
        student_question=clean_q,
    )

    settings = get_settings()
    t0 = time.monotonic()
    llm_res = run_with_fallback(
        provider_name=provider_name,
        model_name=model_name,
        system_prompt=SOCRATIC_TUTOR_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=min(max_tokens, 500),
        timeout_seconds=settings.ai_timeout_seconds,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    safe_hint = sanitize_socratic_output(llm_res.text, _extract_forbidden_answer_tokens(ch))
    job = AIGenerationJob(
        organization_id=course.organization_id,
        requested_by=user.id,
        job_type="socratic_tutor",
        provider=llm_res.provider,
        model_name=llm_res.model_name,
        target_challenge_id=ch.id,
        status="fallback_used" if llm_res.used_fallback else "completed",
        prompt_tokens=llm_res.prompt_tokens,
        completion_tokens=llm_res.completion_tokens,
        latency_ms=latency_ms,
        error_code=llm_res.fallback_reason,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()

    return SocraticHintResponse(
        job_id=job.id,
        hint=safe_hint,
        provider=llm_res.provider,
        model_name=llm_res.model_name,
        used_fallback=llm_res.used_fallback,
        failed_attempts=int(failed_attempts),
        safety_reminder=ch.is_safety_critical,
    )
