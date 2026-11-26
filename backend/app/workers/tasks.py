"""Tareas asíncronas para procesamiento en worker (Redis/ARQ o BackgroundTasks)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.certificates.service import render_certificate_pdf_job

logger = logging.getLogger("vistazo.workers")


def run_certificate_pdf_task(certificate_id: str) -> None:
    """Punto de entrada serializable para worker asíncrono de certificados."""
    render_certificate_pdf_job(uuid.UUID(certificate_id), SessionLocal)


def dispatch_certificate_pdf(
    *,
    certificate_id: uuid.UUID,
    background_tasks,
    session_factory: sessionmaker[Session],
) -> str:
    """Encola en Redis si está configurado, o usa BackgroundTasks en modo ligero."""
    settings = get_settings()
    if settings.redis_url:
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
            client.rpush("vistazo:jobs:certificates", str(certificate_id))
            return "redis_queue"
        except Exception as exc:
            logger.warning("Redis no disponible (%s); usando BackgroundTasks local", type(exc).__name__)

    background_tasks.add_task(render_certificate_pdf_job, certificate_id, session_factory)
    return "background_tasks"
