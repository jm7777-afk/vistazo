"""Servicios de negocio para Generador de Lecciones IA, Blueprint Curricular, Guías, Pruebas Fuertes, Visuales Dinámicos y Tutor Socrático."""

from __future__ import annotations

import re
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
    BLUEPRINT_ARCHITECT_SYSTEM_PROMPT,
    DYNAMIC_VISUAL_SYSTEM_PROMPT,
    LESSON_GENERATOR_SYSTEM_PROMPT,
    SOCRATIC_TUTOR_SYSTEM_PROMPT,
    STRONG_EXAM_SYSTEM_PROMPT,
    STUDY_GUIDE_SYSTEM_PROMPT,
    build_blueprint_user_prompt,
    build_dynamic_visual_user_prompt,
    build_lesson_generator_user_prompt,
    build_socratic_user_prompt,
    build_strong_exam_user_prompt,
    build_study_guide_user_prompt,
)
from app.modules.ai_assistant.providers import run_with_fallback
from app.modules.ai_assistant.schemas import (
    BlueprintPayload,
    DynamicVisualPayload,
    GenerateBlueprintRequest,
    GenerateBlueprintResponse,
    GenerateDynamicVisualRequest,
    GenerateDynamicVisualResponse,
    GenerateLessonDraftResponse,
    GenerateStrongExamRequest,
    GenerateStudyGuideRequest,
    GenerateStudyGuideResponse,
    LessonDraftPayload,
    SocraticHintResponse,
    StudyGuideDraftPayload,
)
from app.modules.audit.service import record_audit_log
from app.modules.auth.models import User
from app.modules.challenges.evaluators import get_challenge_handler
from app.modules.challenges.models import Challenge
from app.modules.courses.models import Course, Lesson, LessonVersion, Module, StudyGuide
from app.modules.courses.service import get_scoped_course
from app.modules.curriculum.models import Competency
from app.modules.media.dynamic_visuals import render_structured_diagram_svg
from app.modules.media.models import ChallengeMediaAsset, MediaAsset
from app.modules.media.service import sign_media_url
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


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return f"{slug[:80] or 'tema'}-{uuid.uuid4().hex[:6]}"


def _scope_filter(col, organization_id: uuid.UUID | None):
    return col.is_(None) if organization_id is None else (col == organization_id)


def _get_scoped_lv_for_ai(
    db: Session, lesson_version_id: uuid.UUID, organization_id: uuid.UUID | None
) -> tuple[LessonVersion, Lesson, Course]:
    row = db.execute(
        select(LessonVersion, Lesson, Course)
        .join(Lesson, LessonVersion.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            LessonVersion.id == lesson_version_id,
            _scope_filter(Course.organization_id, organization_id),
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Versión de lección no encontrada en este ámbito")
    return row[0], row[1], row[2]


def _persist_challenges_into_lv(
    db: Session,
    *,
    lv: LessonVersion,
    competency_id: uuid.UUID | None,
    draft_payload: LessonDraftPayload,
) -> list[uuid.UUID]:
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
    return created_ids


def generate_lesson_draft_challenges(
    db: Session,
    *,
    organization_id: uuid.UUID | None,
    user: User,
    lesson_version_id: uuid.UUID,
    competency_id: uuid.UUID | None,
    source_text: str,
) -> GenerateLessonDraftResponse:
    lv, _lesson, course = _get_scoped_lv_for_ai(db, lesson_version_id, organization_id)
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
            raise NotFoundError("Competencia no válida para este ámbito")
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

    created_ids = _persist_challenges_into_lv(
        db, lv=lv, competency_id=competency_id, draft_payload=draft_payload
    )
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
        lesson_summary=lv.summary or "",
        challenges_created=len(created_ids),
        challenge_ids=created_ids,
    )


def generate_strong_exam_challenges(
    db: Session,
    *,
    organization_id: uuid.UUID | None,
    user: User,
    payload: GenerateStrongExamRequest,
) -> GenerateLessonDraftResponse:
    """Genera una Prueba de Conocimiento Fuerte en borrador sobre una versión de lección."""
    lv, lesson, course = _get_scoped_lv_for_ai(db, payload.lesson_version_id, organization_id)
    if lv.status != "draft":
        raise ValidationDomainError("Solo se pueden generar retos IA en versiones en estado borrador")

    clean_source = validate_and_sanitize_source_text(payload.source_text, min_len=40)
    provider_name, model_name, max_tokens, daily_limit = get_active_provider_config(db)
    _enforce_daily_quota(db, organization_id, daily_limit)

    user_prompt = build_strong_exam_user_prompt(
        source_text=clean_source,
        education_level=course.education_level,
        ui_profile=course.ui_profile,
        difficulty_target=payload.difficulty_target,
        question_count=payload.question_count,
        focus_notes=payload.focus_notes,
    )

    settings = get_settings()
    t0 = time.monotonic()
    llm_res = run_with_fallback(
        provider_name=provider_name,
        model_name=model_name,
        system_prompt=STRONG_EXAM_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        timeout_seconds=settings.ai_timeout_seconds,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    job = AIGenerationJob(
        organization_id=organization_id,
        requested_by=user.id,
        job_type="strong_exam",
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
        draft_payload = LessonDraftPayload.model_validate(raw_json)
    except (ValidationError, ValidationDomainError) as exc:
        job.status = "failed"
        job.error_code = "invalid_ai_schema"
        db.add(job)
        db.commit()
        raise ValidationDomainError(f"La salida IA de Prueba Fuerte no cumplió el esquema: {exc}") from exc

    lesson.lesson_type = "strong_exam"
    if lesson.passing_score_pct < 80:
        lesson.passing_score_pct = 85

    created_ids = _persist_challenges_into_lv(
        db, lv=lv, competency_id=payload.competency_id, draft_payload=draft_payload
    )
    db.add(job)
    record_audit_log(
        db,
        action="ai.strong_exam_generated",
        resource_type="lesson_version",
        resource_id=lv.id,
        organization_id=organization_id,
        actor_user_id=user.id,
        details={"challenges_created": len(created_ids), "difficulty_target": payload.difficulty_target},
    )
    db.commit()
    return GenerateLessonDraftResponse(
        job_id=job.id,
        provider=llm_res.provider,
        model_name=llm_res.model_name,
        status=job.status,
        used_fallback=llm_res.used_fallback,
        lesson_summary=lv.summary or "",
        challenges_created=len(created_ids),
        challenge_ids=created_ids,
    )


def generate_course_blueprint(
    db: Session,
    *,
    organization_id: uuid.UUID | None,
    user: User,
    payload: GenerateBlueprintRequest,
) -> GenerateBlueprintResponse:
    """Genera pensum, módulos, nodos, metodología y guía de estudio, con guardado opcional en borrador."""
    clean_notes = (
        validate_and_sanitize_source_text(payload.source_text, min_len=0, max_len=10000)
        if payload.source_text.strip()
        else ""
    )
    provider_name, model_name, max_tokens, daily_limit = get_active_provider_config(db)
    _enforce_daily_quota(db, organization_id, daily_limit)

    user_prompt = build_blueprint_user_prompt(
        topic=strip_unsafe_markup(payload.topic),
        education_level=payload.education_level,
        ui_profile=payload.ui_profile,
        pedagogy_style=payload.pedagogy_style,
        modules_count=payload.modules_count,
        source_text=clean_notes,
    )

    settings = get_settings()
    t0 = time.monotonic()
    llm_res = run_with_fallback(
        provider_name=provider_name,
        model_name=model_name,
        system_prompt=BLUEPRINT_ARCHITECT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        timeout_seconds=settings.ai_timeout_seconds,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    job = AIGenerationJob(
        organization_id=organization_id,
        requested_by=user.id,
        job_type="blueprint_architect",
        provider=llm_res.provider,
        model_name=llm_res.model_name,
        status="fallback_used" if llm_res.used_fallback else "completed",
        prompt_tokens=llm_res.prompt_tokens,
        completion_tokens=llm_res.completion_tokens,
        latency_ms=latency_ms,
        error_code=llm_res.fallback_reason,
        completed_at=datetime.now(timezone.utc),
    )

    try:
        raw_json = extract_json_object(llm_res.text)
        blueprint = BlueprintPayload.model_validate(raw_json)
    except (ValidationError, ValidationDomainError) as exc:
        job.status = "failed"
        job.error_code = "invalid_ai_schema"
        db.add(job)
        db.commit()
        raise ValidationDomainError(f"La salida IA de arquitectura curricular no es válida: {exc}") from exc

    created_course_id: uuid.UUID | None = None
    created_guide_id: uuid.UUID | None = None

    if payload.save_to_course:
        if payload.target_course_id:
            course = get_scoped_course(db, payload.target_course_id, organization_id)
        else:
            course = Course(
                organization_id=organization_id,
                title=strip_unsafe_markup(blueprint.course_title),
                slug=_slugify(blueprint.course_title),
                description=strip_unsafe_markup(blueprint.course_description),
                education_level=payload.education_level,
                ui_profile=payload.ui_profile,
                visibility="public" if organization_id is None else "institutional",
                status="draft",
                created_by=user.id,
            )
            db.add(course)
            db.flush()
        created_course_id = course.id

        max_mod_order = db.scalar(
            select(func.coalesce(func.max(Module.order_index), 0)).where(
                Module.course_id == course.id, Module.deleted_at.is_(None)
            )
        )
        m_order = int(max_mod_order or 0) + 1
        for mod_draft in blueprint.modules:
            mod = Module(
                course_id=course.id,
                title=strip_unsafe_markup(mod_draft.title),
                description=strip_unsafe_markup(mod_draft.description),
                order_index=m_order,
            )
            db.add(mod)
            db.flush()
            m_order += 1

            for l_idx, les_draft in enumerate(mod_draft.lessons, start=1):
                lesson = Lesson(
                    module_id=mod.id,
                    title=strip_unsafe_markup(les_draft.title),
                    slug=_slugify(les_draft.title),
                    order_index=l_idx,
                    estimated_minutes=les_draft.estimated_minutes,
                    lesson_type=les_draft.lesson_type,
                    passing_score_pct=les_draft.passing_score_pct,
                    is_safety_critical=les_draft.is_safety_critical,
                )
                db.add(lesson)
                db.flush()
                lv = LessonVersion(
                    lesson_id=lesson.id,
                    version_number=1,
                    summary="; ".join(les_draft.key_concepts)[:400] or "Borrador estructurado por IA",
                    status="draft",
                )
                db.add(lv)

        guide = StudyGuide(
            organization_id=organization_id,
            course_id=course.id,
            guide_type="pensum",
            title=f"Metodología y Pensum: {blueprint.course_title}"[:200],
            content_markdown=blueprint.study_guide_markdown,
            methodology_json=blueprint.methodology,
            status="draft",
            ai_generated=True,
            created_by=user.id,
        )
        db.add(guide)
        db.flush()
        created_guide_id = guide.id

    db.add(job)
    record_audit_log(
        db,
        action="ai.blueprint_generated",
        resource_type="course",
        resource_id=created_course_id,
        organization_id=organization_id,
        actor_user_id=user.id,
        details={"saved": payload.save_to_course, "modules": len(blueprint.modules)},
    )
    db.commit()

    return GenerateBlueprintResponse(
        job_id=job.id,
        provider=llm_res.provider,
        model_name=llm_res.model_name,
        status=job.status,
        used_fallback=llm_res.used_fallback,
        blueprint=blueprint,
        created_course_id=created_course_id,
        created_guide_id=created_guide_id,
    )


def generate_study_guide_with_ai(
    db: Session,
    *,
    organization_id: uuid.UUID | None,
    user: User,
    payload: GenerateStudyGuideRequest,
) -> GenerateStudyGuideResponse:
    """Genera una guía de estudio, temario o metodología profesional con IA."""
    if payload.course_id is not None:
        get_scoped_course(db, payload.course_id, organization_id)

    clean_notes = (
        validate_and_sanitize_source_text(payload.source_text, min_len=0, max_len=10000)
        if payload.source_text.strip()
        else ""
    )
    provider_name, model_name, max_tokens, daily_limit = get_active_provider_config(db)
    _enforce_daily_quota(db, organization_id, daily_limit)

    user_prompt = build_study_guide_user_prompt(
        topic=strip_unsafe_markup(payload.topic),
        guide_type=payload.guide_type,
        education_level=payload.education_level,
        pedagogy_style=payload.pedagogy_style,
        source_text=clean_notes,
    )

    settings = get_settings()
    t0 = time.monotonic()
    llm_res = run_with_fallback(
        provider_name=provider_name,
        model_name=model_name,
        system_prompt=STUDY_GUIDE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=max_tokens,
        timeout_seconds=settings.ai_timeout_seconds,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    job = AIGenerationJob(
        organization_id=organization_id,
        requested_by=user.id,
        job_type="study_guide",
        provider=llm_res.provider,
        model_name=llm_res.model_name,
        status="fallback_used" if llm_res.used_fallback else "completed",
        prompt_tokens=llm_res.prompt_tokens,
        completion_tokens=llm_res.completion_tokens,
        latency_ms=latency_ms,
        error_code=llm_res.fallback_reason,
        completed_at=datetime.now(timezone.utc),
    )

    try:
        raw_json = extract_json_object(llm_res.text)
        guide_draft = StudyGuideDraftPayload.model_validate(raw_json)
    except (ValidationError, ValidationDomainError) as exc:
        job.status = "failed"
        job.error_code = "invalid_ai_schema"
        db.add(job)
        db.commit()
        raise ValidationDomainError(f"La guía generada por IA no es válida: {exc}") from exc

    saved_id: uuid.UUID | None = None
    if payload.save_as_draft:
        guide = StudyGuide(
            organization_id=organization_id,
            course_id=payload.course_id,
            lesson_id=payload.lesson_id,
            guide_type=payload.guide_type,
            title=strip_unsafe_markup(guide_draft.title)[:200],
            content_markdown=guide_draft.content_markdown,
            methodology_json=guide_draft.methodology_json,
            status="draft",
            ai_generated=True,
            created_by=user.id,
        )
        db.add(guide)
        db.flush()
        saved_id = guide.id

    db.add(job)
    db.commit()
    return GenerateStudyGuideResponse(
        job_id=job.id,
        provider=llm_res.provider,
        model_name=llm_res.model_name,
        status=job.status,
        used_fallback=llm_res.used_fallback,
        title=guide_draft.title,
        content_markdown=guide_draft.content_markdown,
        methodology_json=guide_draft.methodology_json,
        saved_guide_id=saved_id,
    )


def generate_dynamic_visual_with_ai(
    db: Session,
    *,
    organization_id: uuid.UUID | None,
    user: User,
    payload: GenerateDynamicVisualRequest,
) -> GenerateDynamicVisualResponse:
    """Genera una imagen dinámica SVG interactiva persistida en BD y opcionalmente crea un reto."""
    clean_ctx = (
        validate_and_sanitize_source_text(payload.context_text, min_len=0, max_len=6000)
        if payload.context_text.strip()
        else ""
    )
    provider_name, model_name, max_tokens, daily_limit = get_active_provider_config(db)
    _enforce_daily_quota(db, organization_id, daily_limit)

    user_prompt = build_dynamic_visual_user_prompt(
        topic=strip_unsafe_markup(payload.topic),
        diagram_kind=payload.diagram_kind,
        education_level=payload.education_level,
        context_text=clean_ctx,
    )

    settings = get_settings()
    t0 = time.monotonic()
    llm_res = run_with_fallback(
        provider_name=provider_name,
        model_name=model_name,
        system_prompt=DYNAMIC_VISUAL_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=min(max_tokens, 1600),
        timeout_seconds=settings.ai_timeout_seconds,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    job = AIGenerationJob(
        organization_id=organization_id,
        requested_by=user.id,
        job_type="dynamic_visual",
        provider=llm_res.provider,
        model_name=llm_res.model_name,
        target_lesson_version_id=payload.lesson_version_id,
        status="fallback_used" if llm_res.used_fallback else "completed",
        prompt_tokens=llm_res.prompt_tokens,
        completion_tokens=llm_res.completion_tokens,
        latency_ms=latency_ms,
        error_code=llm_res.fallback_reason,
        completed_at=datetime.now(timezone.utc),
    )

    try:
        raw_json = extract_json_object(llm_res.text)
        vis_payload = DynamicVisualPayload.model_validate(raw_json)
    except (ValidationError, ValidationDomainError) as exc:
        job.status = "failed"
        job.error_code = "invalid_ai_schema"
        db.add(job)
        db.commit()
        raise ValidationDomainError(f"La especificación de imagen dinámica no es válida: {exc}") from exc

    spec_dict = {
        "title": vis_payload.title,
        "subtitle": vis_payload.subtitle,
        "template": vis_payload.template,
        "nodes": vis_payload.nodes,
    }
    svg_markup, zones = render_structured_diagram_svg(spec_dict)
    spec_dict["zones"] = zones

    asset_id = uuid.uuid4()
    asset = MediaAsset(
        id=asset_id,
        organization_id=organization_id,
        uploaded_by=user.id,
        title=vis_payload.title[:200],
        description=vis_payload.subtitle,
        tags_json=[vis_payload.template, "ia-dinamico"],
        education_level=payload.education_level,
        visibility="public" if organization_id is None else "institutional",
        media_format="svg",
        mime_type="image/svg+xml",
        storage_key=f"dynamic/{organization_id or 'global'}/{asset_id}.svg",
        byte_size=max(1, len(svg_markup.encode("utf-8"))),
        processing_status="ready",
        svg_markup=svg_markup,
        dynamic_spec_json=spec_dict,
    )
    db.add(asset)
    db.flush()

    created_challenge_id: uuid.UUID | None = None
    if payload.create_interactive_challenge and payload.lesson_version_id:
        lv, _les, _course = _get_scoped_lv_for_ai(db, payload.lesson_version_id, organization_id)
        max_order = db.scalar(
            select(func.coalesce(func.max(Challenge.order_index), 0)).where(
                Challenge.lesson_version_id == lv.id, Challenge.deleted_at.is_(None)
            )
        )
        valid_zone_ids = {z["id"] for z in zones}
        correct_id = vis_payload.correct_node_id if vis_payload.correct_node_id in valid_zone_ids else zones[0]["id"]
        handler = get_challenge_handler("interactive_zones", 1)
        clean_p, clean_k = handler.validate_definition(
            {
                "instruction": "Haz clic sobre el nodo correcto dentro del diagrama dinámico.",
                "diagram_media_id": str(asset.id),
                "aspect_ratio": "16:9",
                "selection_mode": "single",
                "zones": zones,
            },
            {"correct_zone_ids": [correct_id], "accept_coordinates_within_zones": True},
        )
        ch = Challenge(
            lesson_version_id=lv.id,
            challenge_type="interactive_zones",
            schema_version=1,
            order_index=int(max_order or 0) + 1,
            prompt=strip_unsafe_markup(vis_payload.recommended_question),
            payload_json=clean_p,
            answer_key_json=clean_k,
            pedagogical_explanation=strip_unsafe_markup(vis_payload.explanation),
            difficulty=2,
            points=15,
            estimated_seconds=45,
            is_safety_critical=False,
            status="draft" if lv.status == "draft" else "published",
            ai_generated=True,
        )
        db.add(ch)
        db.flush()
        db.add(
            ChallengeMediaAsset(
                challenge_id=ch.id,
                media_asset_id=asset.id,
                role="diagram",
                order_index=0,
            )
        )
        created_challenge_id = ch.id

    db.add(job)
    db.commit()
    signed_url, _exp = sign_media_url(asset.id)
    return GenerateDynamicVisualResponse(
        job_id=job.id,
        provider=llm_res.provider,
        model_name=llm_res.model_name,
        status=job.status,
        used_fallback=llm_res.used_fallback,
        media_asset_id=asset.id,
        signed_url=signed_url,
        title=asset.title,
        template=vis_payload.template,
        zones=zones,
        created_challenge_id=created_challenge_id,
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
