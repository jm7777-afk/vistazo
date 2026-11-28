"""Endpoints SaaS de planes, cuotas organizacionales, checkout y webhook de Stripe."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, require_permission
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.db.session import get_db
from app.modules.audit.service import record_audit_log
from app.modules.billing.models import OrganizationSubscription

router = APIRouter(tags=["billing"])

PLAN_CATALOG = [
    {
        "plan_code": "free",
        "name": "Inicial / Estudio Libre",
        "price_monthly_usd": 0,
        "max_students": 30,
        "monthly_ai_limit": 100,
        "features": ["CRUD completo de cursos y guías", "Hasta 30 estudiantes por organización", "100 generaciones IA/mes"],
    },
    {
        "plan_code": "educator_pro",
        "name": "Educador Pro",
        "price_monthly_usd": 19,
        "max_students": 250,
        "monthly_ai_limit": 1000,
        "features": ["Hasta 250 estudiantes", "1,000 generaciones IA/mes", "Exportación PDF y Clase en Vivo ilimitada"],
    },
    {
        "plan_code": "institution",
        "name": "Academia / Universidad",
        "price_monthly_usd": 79,
        "max_students": 5000,
        "monthly_ai_limit": 10000,
        "features": ["Hasta 5,000 estudiantes", "10,000 generaciones IA/mes", "Certificados QR masivos y soporte prioritario"],
    },
]

PLAN_QUOTAS = {p["plan_code"]: (p["max_students"], p["monthly_ai_limit"]) for p in PLAN_CATALOG}


class SubscriptionOut(BaseModel):
    organization_id: uuid.UUID
    plan_code: str
    status: str
    max_students: int
    monthly_ai_limit: int
    current_period_end: datetime | None = None


class CheckoutRequest(BaseModel):
    plan_code: Literal["free", "educator_pro", "institution"]


class CheckoutResponse(BaseModel):
    mode: str
    subscription: SubscriptionOut
    checkout_url: str | None = None


@router.get("/billing/plans")
def list_billing_plans() -> list[dict]:
    return PLAN_CATALOG


@router.get("/orgs/{org_id}/billing", response_model=SubscriptionOut)
def get_org_subscription(
    tenant: TenantContext = Depends(require_permission("org:manage")),
    db: Session = Depends(get_db),
) -> SubscriptionOut:
    sub = db.scalar(
        select(OrganizationSubscription).where(OrganizationSubscription.organization_id == tenant.organization.id)
    )
    if not sub:
        sub = OrganizationSubscription(
            organization_id=tenant.organization.id,
            owner_user_id=tenant.user.id,
            plan_code="free",
            status="active",
            max_students=30,
            monthly_ai_limit=100,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return SubscriptionOut(
        organization_id=sub.organization_id,
        plan_code=sub.plan_code,
        status=sub.status,
        max_students=sub.max_students,
        monthly_ai_limit=sub.monthly_ai_limit,
        current_period_end=sub.current_period_end,
    )


@router.post("/orgs/{org_id}/billing/checkout", response_model=CheckoutResponse)
def upgrade_org_subscription(
    payload: CheckoutRequest,
    tenant: TenantContext = Depends(require_permission("org:manage")),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    max_stu, ai_lim = PLAN_QUOTAS[payload.plan_code]
    sub = db.scalar(
        select(OrganizationSubscription).where(OrganizationSubscription.organization_id == tenant.organization.id)
    )
    if not sub:
        sub = OrganizationSubscription(
            organization_id=tenant.organization.id,
            owner_user_id=tenant.user.id,
        )
        db.add(sub)

    sub.plan_code = payload.plan_code
    sub.status = "active"
    sub.max_students = int(max_stu)
    sub.monthly_ai_limit = int(ai_lim)
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)

    record_audit_log(
        db,
        action="billing.plan_updated",
        resource_type="organization_subscription",
        organization_id=tenant.organization.id,
        actor_user_id=tenant.user.id,
        details={"plan_code": payload.plan_code},
    )
    db.commit()
    db.refresh(sub)

    return CheckoutResponse(
        mode="sandbox_instant" if not get_settings().stripe_secret_key else "stripe_configured",
        subscription=SubscriptionOut(
            organization_id=sub.organization_id,
            plan_code=sub.plan_code,
            status=sub.status,
            max_students=sub.max_students,
            monthly_ai_limit=sub.monthly_ai_limit,
            current_period_end=sub.current_period_end,
        ),
        checkout_url=None,
    )


@router.post("/billing/webhooks/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    raw_body = await request.body()
    secret = get_settings().stripe_webhook_secret
    if secret:
        if not stripe_signature:
            raise UnauthorizedError("Firma Stripe-Signature ausente")
        parts = dict(item.split("=", 1) for item in stripe_signature.split(",") if "=" in item)
        ts = parts.get("t", "")
        sig_v1 = parts.get("v1", "")
        signed_payload = f"{ts}.".encode("utf-8") + raw_body
        expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig_v1):
            raise UnauthorizedError("Firma Stripe inválida")

    event = json.loads(raw_body.decode("utf-8") or "{}")
    data_obj = (event.get("data") or {}).get("object") or {}
    meta = data_obj.get("metadata") or {}
    org_id_raw = meta.get("organization_id")
    plan_code = meta.get("plan_code")
    if org_id_raw and plan_code in PLAN_QUOTAS:
        sub = db.scalar(
            select(OrganizationSubscription).where(OrganizationSubscription.organization_id == uuid.UUID(org_id_raw))
        )
        if sub:
            max_stu, ai_lim = PLAN_QUOTAS[plan_code]
            sub.plan_code = plan_code
            sub.max_students = int(max_stu)
            sub.monthly_ai_limit = int(ai_lim)
            sub.status = "active"
            db.commit()

    return {"received": "ok"}
