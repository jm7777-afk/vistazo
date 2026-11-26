"""Guardrails de seguridad para entradas y salidas de IA pedagógica."""

from __future__ import annotations

import json
import re

from app.core.exceptions import ValidationDomainError

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"ignora\s+(todas\s+)?las\s+instrucciones\s+(anteriores|previas)", re.IGNORECASE),
    re.compile(r"(reveal|show|print|dump)\s+(the\s+)?(system\s+prompt|developer\s+prompt|api[_\s]?key)", re.IGNORECASE),
    re.compile(r"(revela|muestra|dime)\s+(el\s+)?(system\s+prompt|answer[_\s]?key|api[_\s]?key)", re.IGNORECASE),
    re.compile(r"<\s*system\s*>|</\s*instructor_source_text\s*>", re.IGNORECASE),
    re.compile(r"\bjailbreak\b|\bDAN\s+mode\b", re.IGNORECASE),
]

HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def strip_unsafe_markup(text: str) -> str:
    """Elimina etiquetas HTML/script para mitigar XSS en salidas o entradas."""
    return HTML_TAG_PATTERN.sub("", text).strip()


def validate_and_sanitize_source_text(text: str, *, min_len: int = 80, max_len: int = 8000) -> str:
    """Valida longitud y bloquea intentos explícitos de prompt injection."""
    cleaned = strip_unsafe_markup(text)
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(cleaned):
            raise ValidationDomainError(
                "El texto contiene directivas no permitidas (posible prompt injection)",
                code="prompt_injection_detected",
            )
    if len(cleaned) < min_len:
        raise ValidationDomainError(
            f"El texto fuente debe tener al menos {min_len} caracteres útiles",
            code="insufficient_source_content",
        )
    if len(cleaned) > max_len:
        raise ValidationDomainError(
            f"El texto fuente no puede exceder {max_len} caracteres",
            code="source_text_too_long",
        )
    return cleaned


def validate_student_question(text: str | None) -> str:
    """Valida pregunta opcional del estudiante al Tutor Socrático."""
    if not text:
        return ""
    cleaned = strip_unsafe_markup(text)
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(cleaned):
            raise ValidationDomainError(
                "Entrada bloqueada por políticas de seguridad del tutor",
                code="prompt_injection_detected",
            )
    return cleaned[:500]


def extract_json_object(raw_text: str) -> dict:
    """Extrae un objeto JSON desde la respuesta del modelo eliminando cercas markdown."""
    candidate = raw_text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValidationDomainError(f"La respuesta IA no es un JSON válido: {exc.msg}", code="ai_invalid_json") from exc
    if not isinstance(parsed, dict):
        raise ValidationDomainError("La respuesta IA debe ser un objeto JSON", code="ai_invalid_json")
    return parsed


def sanitize_socratic_output(text: str, forbidden_answer_tokens: list[str]) -> str:
    """Sanitiza HTML y oculta coincidencias literales de la respuesta correcta."""
    cleaned = strip_unsafe_markup(text)
    for token in forbidden_answer_tokens:
        norm = token.strip()
        if len(norm) >= 4:
            cleaned = re.sub(re.escape(norm), "[concepto clave]", cleaned, flags=re.IGNORECASE)
    return cleaned[:900]
