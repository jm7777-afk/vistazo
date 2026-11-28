"""Endpoints de notificaciones inteligentes, recordatorios de estudio y suscripciones Push PWA."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.mailer import send_email_notification
from app.db.session import get_db
from app.modules.auth.models import ParentalConsent, User
from app.modules.gamification.models import StudentGamificationProfile
from app.modules.notifications.models import PushSubscription
from app.modules.spaced_repetition.models import SpacedRepetitionItem

router = APIRouter(prefix="/notifications", tags=["notifications"])


class ReminderItem(BaseModel):
    id: str
    kind: str
    title: str
    body: str
    action_url: str


class NotificationsSummaryOut(BaseModel):
    due_reviews_count: int
    current_streak_days: int
    email_verified: bool
    reminders: list[ReminderItem]


class PushSubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=4, max_length=2000)
    subscription_json: dict = Field(default_factory=dict)
    device_label: str = Field(default="Web PWA", max_length=120)


@router.get("/me", response_model=NotificationsSummaryOut)
def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationsSummaryOut:
    now = datetime.now(timezone.utc)
    due_count = int(
        db.scalar(
            select(func.count(SpacedRepetitionItem.id)).where(
                SpacedRepetitionItem.user_id == current_user.id,
                SpacedRepetitionItem.next_review_at <= now,
            )
        )
        or 0
    )
    gam = db.scalar(
        select(StudentGamificationProfile).where(StudentGamificationProfile.user_id == current_user.id)
    )
    streak = gam.current_streak_days if gam else 0

    reminders: list[ReminderItem] = []
    if due_count > 0:
        reminders.append(
            ReminderItem(
                id="sm2-due",
                kind="spaced_repetition",
                title=f"Tienes {due_count} repasos espaciados pendientes",
                body="Refrescar estos retos hoy evita que caiga tu retención a largo plazo.",
                action_url="/reviews",
            )
        )
    if streak > 0:
        reminders.append(
            ReminderItem(
                id="streak-keep",
                kind="streak",
                title=f"Racha activa de {streak} días",
                body="Completa una microlección rápida para mantener tu racha intacta.",
                action_url="/catalog",
            )
        )
    if current_user.is_minor:
        consent = db.scalar(select(ParentalConsent).where(ParentalConsent.minor_user_id == current_user.id))
        if consent and consent.consent_status == "pending":
            reminders.append(
                ReminderItem(
                    id="parental-pending",
                    kind="compliance",
                    title="Autorización parental pendiente",
                    body="Tu representante legal debe aprobar el enlace enviado a su correo.",
                    action_url="/profile",
                )
            )
    if not current_user.email_verified:
        reminders.append(
            ReminderItem(
                id="verify-email",
                kind="account",
                title="Verifica tu correo electrónico",
                body="Mantén tu cuenta protegida y habilita recuperación de contraseña.",
                action_url="/recuperar-cuenta",
            )
        )

    return NotificationsSummaryOut(
        due_reviews_count=due_count,
        current_streak_days=streak,
        email_verified=current_user.email_verified,
        reminders=reminders,
    )


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
def subscribe_push_notifications(
    payload: PushSubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    existing = db.scalar(
        select(PushSubscription).where(
            PushSubscription.user_id == current_user.id,
            PushSubscription.endpoint == payload.endpoint,
        )
    )
    if not existing:
        db.add(
            PushSubscription(
                user_id=current_user.id,
                endpoint=payload.endpoint,
                subscription_json=payload.subscription_json,
                device_label=payload.device_label,
                is_active=True,
            )
        )
    else:
        existing.is_active = True
        existing.subscription_json = payload.subscription_json
    db.commit()
    return {"status": "subscribed"}


@router.post("/send-study-reminder")
def trigger_study_reminder_email(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    due_count = int(
        db.scalar(
            select(func.count(SpacedRepetitionItem.id)).where(
                SpacedRepetitionItem.user_id == current_user.id,
                SpacedRepetitionItem.next_review_at <= now,
            )
        )
        or 0
    )
    sent = send_email_notification(
        to_email=current_user.email,
        subject="Recordatorio de estudio — Vistazo LMS",
        body_text=(
            f"Hola {current_user.full_name},\n\n"
            f"Tienes {due_count} retos listos para repaso espaciado hoy en Vistazo.\n"
        ),
    )
    return {"status": "sent" if sent else "queued_local"}
