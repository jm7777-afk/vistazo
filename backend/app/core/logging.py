"""Configuración de logging estructurado sin exposición de secretos."""

from __future__ import annotations

import logging
import re

SENSITIVE_PATTERN = re.compile(
    r"(password|token|authorization|secret|cookie|api_key)\s*[=:]\s*\S+",
    re.IGNORECASE,
)


class RedactingFilter(logging.Filter):
    """Enmascara patrones de credenciales antes de emitir registros."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = SENSITIVE_PATTERN.sub(r"\1=[REDACTED]", record.msg)
        return True


def configure_logging() -> logging.Logger:
    """Inicializa el logger principal de la aplicación."""
    logger = logging.getLogger("vistazo")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
        )
        handler.setFormatter(formatter)
        handler.addFilter(RedactingFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
