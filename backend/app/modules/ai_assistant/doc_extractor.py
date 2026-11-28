"""Extractor seguro de texto desde documentos PDF, DOCX y texto plano para Asistente IA."""

from __future__ import annotations

import io
from pathlib import Path

from app.core.exceptions import ValidationDomainError
from app.modules.ai_assistant.guardrails import validate_and_sanitize_source_text

MAX_DOC_BYTES = 10 * 1024 * 1024  # 10 MB


def extract_text_from_uploaded_document(filename: str, content: bytes) -> str:
    """Extrae texto limpio de PDF, DOCX, TXT, MD, CSV o JSON validando tamaño y seguridad."""
    if not content or len(content) > MAX_DOC_BYTES:
        raise ValidationDomainError(
            "El documento debe estar entre 1 byte y 10 MB",
            code="invalid_document_size",
        )

    ext = Path(filename or "doc.txt").suffix.lower()
    raw_text = ""

    if ext == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            chunks = [page.extract_text() or "" for page in reader.pages[:40]]
            raw_text = "\n".join(chunks)
        except Exception as exc:
            raise ValidationDomainError(f"No se pudo leer el PDF: {exc}", code="pdf_read_error") from exc
    elif ext == ".docx":
        try:
            from docx import Document

            doc = Document(io.BytesIO(content))
            raw_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as exc:
            raise ValidationDomainError(f"No se pudo leer el archivo DOCX: {exc}", code="docx_read_error") from exc
    elif ext in {".txt", ".md", ".csv", ".json"}:
        raw_text = content.decode("utf-8", errors="ignore")
    else:
        raise ValidationDomainError(
            "Formato no soportado. Usa PDF, DOCX, TXT, MD, CSV o JSON.",
            code="unsupported_document_format",
        )

    trimmed = raw_text.strip()[:10000]
    return validate_and_sanitize_source_text(trimmed, min_len=10, max_len=10000)
