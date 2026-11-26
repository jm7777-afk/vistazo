"""Servicio para registro inmutable de eventos de auditoría."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog


def record_audit_log(
    db: Session,
    *,
    action: str,
    resource_type: str,
    outcome: str = "success",
    organization_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    resource_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    details: dict | None = None,
) -> AuditLog:
    """Inserta un evento de auditoría en la sesión actual."""
    entry = AuditLog(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        ip_address=ip_address,
        details_json=details or {},
    )
    db.add(entry)
    return entry
