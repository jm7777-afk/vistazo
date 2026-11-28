"""Servicio ligero de envío de correos SMTP con modo seguro sin bloqueo cuando no hay SMTP configurado."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger("vistazo.mailer")


def send_email_notification(*, to_email: str, subject: str, body_text: str) -> bool:
    """Envía un correo transaccional vía SMTP STARTTLS. Devuelve True si se envió."""
    settings = get_settings()
    if not settings.smtp_host:
        logger.info("SMTP no configurado; notificación omitida para asunto '%s'", subject)
        return False

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body_text)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception as exc:
        logger.warning("Fallo al enviar correo SMTP: %s", type(exc).__name__)
        return False
