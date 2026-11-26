"""Endpoints de Asistente Pedagógico IA y administración de proveedores."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_current_user, require_permission, require_super_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.modules.ai_assistant.models import AIGenerationJob, AIProviderConfig
from app.modules.ai_assistant.schemas import (
    AIJobOut,
    AIProviderConfigOut,
    AIProviderUpdateRequest,
    GenerateLessonDraftRequest,
    GenerateLessonDraftResponse,
    SocraticHintRequest,
    SocraticHintResponse,
)
from app.modules.ai_assistant.service import generate_lesson_draft_challenges, generate_socratic_hint
from app.modules.audit.service import record_audit_log
from app.modules.auth.models import User

router = APIRouter(tags=["ai_assistant"])


@router.post(
    "/orgs/{org_id}/ai/generate-lesson-draft",
    response_model=GenerateLessonDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_lesson_draft(
    payload: GenerateLessonDraftRequest,
    tenant: TenantContext = Depends(require_permission("ai:generate")),
    db: Session = Depends(get_db),
) -> GenerateLessonDraftResponse:
    return generate_lesson_draft_challenges(
        db,
        organization_id=tenant.organization.id,
        user=tenant.user,
        lesson_version_id=payload.lesson_version_id,
        competency_id=payload.competency_id,
        source_text=payload.source_text,
    )


@router.get("/orgs/{org_id}/ai/jobs", response_model=list[AIJobOut])
def list_org_ai_jobs(
    tenant: TenantContext = Depends(require_permission("ai:generate")),
    db: Session = Depends(get_db),
) -> list[AIJobOut]:
    jobs = db.scalars(
        select(AIGenerationJob)
        .where(AIGenerationJob.organization_id == tenant.organization.id)
        .order_by(AIGenerationJob.created_at.desc())
        .limit(50)
    ).all()
    return [
        AIJobOut(
            id=j.id,
            organization_id=j.organization_id,
            job_type=j.job_type,
            provider=j.provider,
            model_name=j.model_name,
            status=j.status,
            prompt_tokens=j.prompt_tokens,
            completion_tokens=j.completion_tokens,
            latency_ms=j.latency_ms,
            error_code=j.error_code,
            created_at=j.created_at,
        )
        for j in jobs
    ]


@router.post("/challenges/{challenge_id}/socratic-hint", response_model=SocraticHintResponse)
def request_socratic_hint(
    challenge_id: uuid.UUID,
    payload: SocraticHintRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SocraticHintResponse:
    return generate_socratic_hint(
        db,
        user=current_user,
        challenge_id=challenge_id,
        student_question=payload.student_question,
    )


def _has_key(provider: str) -> bool:
    settings = get_settings()
    if provider == "gemini":
        return bool(settings.gemini_api_key)
    if provider == "groq":
        return bool(settings.groq_api_key)
    return True


@router.get("/admin/ai/providers", response_model=list[AIProviderConfigOut])
def list_ai_providers(
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[AIProviderConfigOut]:
    rows = db.scalars(select(AIProviderConfig).order_by(AIProviderConfig.provider.asc())).all()
    return [
        AIProviderConfigOut(
            id=r.id,
            provider=r.provider,
            model_name=r.model_name,
            is_active=r.is_active,
            max_tokens=r.max_tokens,
            daily_org_job_limit=r.daily_org_job_limit,
            has_api_key_configured=_has_key(r.provider),
        )
        for r in rows
    ]


@router.put("/admin/ai/providers", response_model=AIProviderConfigOut)
def set_active_ai_provider(
    payload: AIProviderUpdateRequest,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> AIProviderConfigOut:
    rows = db.scalars(select(AIProviderConfig)).all()
    target: AIProviderConfig | None = None
    for row in rows:
        if row.provider == payload.provider:
            row.is_active = True
            row.model_name = payload.model_name.strip()
            row.max_tokens = payload.max_tokens
            row.daily_org_job_limit = payload.daily_org_job_limit
            target = row
        else:
            row.is_active = False

    if target is None:
        target = AIProviderConfig(
            provider=payload.provider,
            model_name=payload.model_name.strip(),
            is_active=True,
            max_tokens=payload.max_tokens,
            daily_org_job_limit=payload.daily_org_job_limit,
        )
        db.add(target)
        db.flush()

    record_audit_log(
        db,
        action="ai.provider_updated",
        resource_type="ai_provider_config",
        resource_id=target.id,
        actor_user_id=admin.id,
        details={"provider": target.provider, "model_name": target.model_name},
    )
    db.commit()
    db.refresh(target)
    return AIProviderConfigOut(
        id=target.id,
        provider=target.provider,
        model_name=target.model_name,
        is_active=target.is_active,
        max_tokens=target.max_tokens,
        daily_org_job_limit=target.daily_org_job_limit,
        has_api_key_configured=_has_key(target.provider),
    )
