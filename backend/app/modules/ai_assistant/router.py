"""Endpoints de Asistente Pedagógico IA (Org + SuperAdmin) y administración de proveedores."""

from __future__ import annotations

import uuid

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import TenantContext, get_current_user, require_permission, require_super_admin
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.db.session import get_db, get_session_factory
from app.modules.ai_assistant.doc_extractor import extract_text_from_uploaded_document
from app.modules.ai_assistant.models import AIGenerationJob, AIProviderConfig, AsyncTaskRecord
from app.modules.ai_assistant.schemas import (
    AIJobOut,
    AIProviderConfigOut,
    AIProviderUpdateRequest,
    AdaptiveRemediationRequest,
    AdaptiveRemediationResponse,
    DocumentExtractResponse,
    GenerateBlueprintRequest,
    GenerateBlueprintResponse,
    GenerateDynamicVisualRequest,
    GenerateDynamicVisualResponse,
    GenerateLessonDraftRequest,
    GenerateLessonDraftResponse,
    GenerateStrongExamRequest,
    GenerateStudyGuideRequest,
    GenerateStudyGuideResponse,
    SocraticHintRequest,
    SocraticHintResponse,
)
from app.modules.ai_assistant.service import (
    generate_adaptive_remediation,
    generate_course_blueprint,
    generate_dynamic_visual_with_ai,
    generate_lesson_draft_challenges,
    generate_socratic_hint,
    generate_strong_exam_challenges,
    generate_study_guide_with_ai,
)
from app.modules.audit.service import record_audit_log
from app.modules.auth.models import User

router = APIRouter(tags=["ai_assistant"])


# ---------------------------------------------------------------------------
# Endpoints IA Organizacionales (Educador / Coordinador / Instructor)
# ---------------------------------------------------------------------------
@router.post(
    "/orgs/{org_id}/ai/generate-lesson-draft",
    response_model=GenerateLessonDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_org_lesson_draft(
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


@router.post(
    "/orgs/{org_id}/ai/generate-blueprint",
    response_model=GenerateBlueprintResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_org_blueprint(
    payload: GenerateBlueprintRequest,
    tenant: TenantContext = Depends(require_permission("ai:generate")),
    db: Session = Depends(get_db),
) -> GenerateBlueprintResponse:
    return generate_course_blueprint(
        db, organization_id=tenant.organization.id, user=tenant.user, payload=payload
    )


@router.post(
    "/orgs/{org_id}/ai/generate-study-guide",
    response_model=GenerateStudyGuideResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_org_study_guide(
    payload: GenerateStudyGuideRequest,
    tenant: TenantContext = Depends(require_permission("ai:generate")),
    db: Session = Depends(get_db),
) -> GenerateStudyGuideResponse:
    return generate_study_guide_with_ai(
        db, organization_id=tenant.organization.id, user=tenant.user, payload=payload
    )


@router.post(
    "/orgs/{org_id}/ai/generate-strong-exam",
    response_model=GenerateLessonDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_org_strong_exam(
    payload: GenerateStrongExamRequest,
    tenant: TenantContext = Depends(require_permission("ai:generate")),
    db: Session = Depends(get_db),
) -> GenerateLessonDraftResponse:
    return generate_strong_exam_challenges(
        db, organization_id=tenant.organization.id, user=tenant.user, payload=payload
    )


@router.post(
    "/orgs/{org_id}/ai/generate-dynamic-visual",
    response_model=GenerateDynamicVisualResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_org_dynamic_visual(
    payload: GenerateDynamicVisualRequest,
    tenant: TenantContext = Depends(require_permission("ai:generate")),
    db: Session = Depends(get_db),
) -> GenerateDynamicVisualResponse:
    return generate_dynamic_visual_with_ai(
        db, organization_id=tenant.organization.id, user=tenant.user, payload=payload
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


# ---------------------------------------------------------------------------
# Endpoints IA Globales SuperAdmin (Catálogo Libre)
# ---------------------------------------------------------------------------
@router.post(
    "/admin/ai/generate-lesson-draft",
    response_model=GenerateLessonDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_global_lesson_draft(
    payload: GenerateLessonDraftRequest,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> GenerateLessonDraftResponse:
    return generate_lesson_draft_challenges(
        db,
        organization_id=None,
        user=admin,
        lesson_version_id=payload.lesson_version_id,
        competency_id=payload.competency_id,
        source_text=payload.source_text,
    )


@router.post(
    "/admin/ai/generate-blueprint",
    response_model=GenerateBlueprintResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_global_blueprint(
    payload: GenerateBlueprintRequest,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> GenerateBlueprintResponse:
    return generate_course_blueprint(db, organization_id=None, user=admin, payload=payload)


@router.post(
    "/admin/ai/generate-study-guide",
    response_model=GenerateStudyGuideResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_global_study_guide(
    payload: GenerateStudyGuideRequest,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> GenerateStudyGuideResponse:
    return generate_study_guide_with_ai(db, organization_id=None, user=admin, payload=payload)


@router.post(
    "/admin/ai/generate-strong-exam",
    response_model=GenerateLessonDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_global_strong_exam(
    payload: GenerateStrongExamRequest,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> GenerateLessonDraftResponse:
    return generate_strong_exam_challenges(db, organization_id=None, user=admin, payload=payload)


@router.post(
    "/admin/ai/generate-dynamic-visual",
    response_model=GenerateDynamicVisualResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_global_dynamic_visual(
    payload: GenerateDynamicVisualRequest,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> GenerateDynamicVisualResponse:
    return generate_dynamic_visual_with_ai(db, organization_id=None, user=admin, payload=payload)


@router.get("/admin/ai/jobs", response_model=list[AIJobOut])
def list_global_ai_jobs(
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[AIJobOut]:
    jobs = db.scalars(
        select(AIGenerationJob).order_by(AIGenerationJob.created_at.desc()).limit(50)
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


# ---------------------------------------------------------------------------
# Tutor Socrático y Administración de Proveedores
# ---------------------------------------------------------------------------
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


@router.post("/orgs/{org_id}/ai/extract-document", response_model=DocumentExtractResponse)
def extract_org_document(
    file: UploadFile = File(...),
    _tenant: TenantContext = Depends(require_permission("ai:generate")),
) -> DocumentExtractResponse:
    content = file.file.read()
    text = extract_text_from_uploaded_document(file.filename or "documento.txt", content)
    return DocumentExtractResponse(
        filename=file.filename or "documento.txt",
        char_count=len(text),
        extracted_text=text,
    )


@router.post("/admin/ai/extract-document", response_model=DocumentExtractResponse)
def extract_global_document(
    file: UploadFile = File(...),
    _admin: User = Depends(require_super_admin),
) -> DocumentExtractResponse:
    content = file.file.read()
    text = extract_text_from_uploaded_document(file.filename or "documento.txt", content)
    return DocumentExtractResponse(
        filename=file.filename or "documento.txt",
        char_count=len(text),
        extracted_text=text,
    )


class AsyncTaskOut(BaseModel):
    task_id: uuid.UUID
    task_type: str
    status: str
    result_json: dict | None = None
    error_message: str | None = None


def _run_blueprint_task(
    task_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    user_id: uuid.UUID,
    payload_dict: dict,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        task = db.scalar(select(AsyncTaskRecord).where(AsyncTaskRecord.id == task_id))
        user = db.scalar(select(User).where(User.id == user_id))
        if not task or not user:
            return
        task.status = "running"
        db.commit()
        try:
            req = GenerateBlueprintRequest.model_validate(payload_dict)
            res = generate_course_blueprint(db, organization_id=organization_id, user=user, payload=req)
            task.status = "completed"
            task.result_json = {
                "created_course_id": str(res.created_course_id) if res.created_course_id else None,
                "created_guide_id": str(res.created_guide_id) if res.created_guide_id else None,
                "course_title": res.blueprint.course_title,
                "modules_count": len(res.blueprint.modules),
            }
            task.completed_at = datetime.now(timezone.utc)
        except Exception as exc:
            task.status = "failed"
            task.error_message = str(exc)[:500]
            task.completed_at = datetime.now(timezone.utc)
        db.commit()


@router.post("/orgs/{org_id}/ai/generate-blueprint-async", response_model=AsyncTaskOut, status_code=status.HTTP_202_ACCEPTED)
def queue_org_blueprint_async(
    payload: GenerateBlueprintRequest,
    background_tasks: BackgroundTasks,
    tenant: TenantContext = Depends(require_permission("ai:generate")),
    db: Session = Depends(get_db),
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> AsyncTaskOut:
    task = AsyncTaskRecord(
        organization_id=tenant.organization.id,
        requested_by=tenant.user.id,
        task_type="blueprint_architect",
        status="queued",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    background_tasks.add_task(
        _run_blueprint_task,
        task.id,
        tenant.organization.id,
        tenant.user.id,
        payload.model_dump(mode="json"),
        session_factory,
    )
    return AsyncTaskOut(task_id=task.id, task_type=task.task_type, status=task.status)


@router.get("/tasks/{task_id}", response_model=AsyncTaskOut)
def get_async_task_status(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AsyncTaskOut:
    task = db.scalar(select(AsyncTaskRecord).where(AsyncTaskRecord.id == task_id))
    if not task or (task.requested_by != current_user.id and not current_user.is_super_admin):
        raise NotFoundError("Tarea asíncrona no encontrada")
    return AsyncTaskOut(
        task_id=task.id,
        task_type=task.task_type,
        status=task.status,
        result_json=task.result_json,
        error_message=task.error_message,
    )


@router.post("/ai/adaptive-remediation", response_model=AdaptiveRemediationResponse)
def request_adaptive_remediation(
    payload: AdaptiveRemediationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdaptiveRemediationResponse:
    return generate_adaptive_remediation(
        db,
        user=current_user,
        course_id=payload.course_id,
        missed_prompts=payload.missed_prompts,
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
