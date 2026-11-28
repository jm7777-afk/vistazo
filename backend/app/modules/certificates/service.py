"""Servicios criptográficos, cálculo de nota, PDF con QR, revocación y anti-enumeración."""

from __future__ import annotations

import hashlib
import hmac
import io
import os
import re
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import status as http_status
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError, ValidationDomainError
from app.modules.audit.service import record_audit_log
from app.modules.auth.models import User
from app.modules.certificates.models import Certificate, CertificateRevocation, CertificateSignature
from app.modules.certificates.schemas import PublicCertificateVerificationOut
from app.modules.courses.models import Lesson, LessonVersion, Module
from app.modules.curriculum.models import Classroom, ClassroomMember, CurriculumUnit, CurriculumVersion, Program
from app.modules.progress.models import LessonProgress
from app.modules.tenants.models import Organization, OrganizationMember

HASH_HEX_PATTERN = re.compile(r"^[a-f0-9]{64}$")

_rate_lock = threading.Lock()
_verify_hits: dict[str, deque[float]] = defaultdict(deque)


def reset_verify_rate_limiter() -> None:
    """Reinicia el contador de rate limit (uso en pruebas)."""
    with _rate_lock:
        _verify_hits.clear()


def check_verify_rate_limit(client_ip: str, max_requests: int = 30, window_seconds: int = 60) -> None:
    """Protección contra enumeración por IP en ruta pública de verificación."""
    now = time.monotonic()
    with _rate_lock:
        bucket = _verify_hits[client_ip]
        while bucket and (now - bucket[0]) > window_seconds:
            bucket.popleft()
        if len(bucket) >= max_requests:
            raise AppError(
                code="rate_limit_exceeded",
                message="Demasiadas consultas de verificación; intenta nuevamente en un minuto",
                status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            )
        bucket.append(now)


def get_certificates_storage_root() -> Path:
    root = Path(os.getenv("LOCAL_CERT_ROOT", Path(__file__).resolve().parents[3] / "storage_certificates"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def mask_recipient_name(full_name: str) -> str:
    """Convierte el nombre completo en iniciales seguras sin exponer PII sensible."""
    parts = [p.strip() for p in full_name.split() if p.strip()]
    if not parts:
        return "E."
    return " ".join(f"{p[0].upper()}." for p in parts)


def compute_verification_hash(
    *,
    certificate_id: uuid.UUID,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    curriculum_version_id: uuid.UUID,
    issued_at: datetime,
) -> str:
    salt = secrets.token_hex(16)
    raw = f"{certificate_id}|{organization_id}|{user_id}|{curriculum_version_id}|{issued_at.isoformat()}|{salt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_signature_hash(
    *,
    certificate_number: str,
    verification_hash: str,
    final_grade: Decimal,
    signer_user_id: uuid.UUID,
) -> str:
    settings = get_settings()
    payload = f"{certificate_number}|{verification_hash}|{final_grade}|{signer_user_id}".encode("utf-8")
    return hmac.new(settings.jwt_secret_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def generate_certificate_pdf_bytes(
    *,
    organization_name: str,
    recipient_name: str,
    program_title: str,
    curriculum_title: str,
    certificate_number: str,
    verification_hash: str,
    final_grade: Decimal,
    issued_at: datetime,
    signer_name: str,
    signer_title: str,
    verification_url: str,
) -> bytes:
    """Genera un PDF institucional con código QR de verificación."""
    buf = io.BytesIO()
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))

    # Marco institucional
    c.setStrokeColorRGB(0.06, 0.30, 0.36)
    c.setLineWidth(4)
    c.rect(28, 28, page_w - 56, page_h - 56)

    logo_path = Path(__file__).resolve().parents[2] / "assets" / "vistazo-icon.png"
    if logo_path.exists():
        c.drawImage(str(logo_path), 58, page_h - 115, width=74, height=48, mask="auto", preserveAspectRatio=True)

    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(page_w / 2, page_h - 90, organization_name.upper())

    c.setFont("Helvetica", 13)
    c.drawCentredString(page_w / 2, page_h - 125, "OTORGA EL PRESENTE CERTIFICADO DE COMPETENCIA A")

    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(page_w / 2, page_h - 175, recipient_name)

    c.setFont("Helvetica", 13)
    c.drawCentredString(page_w / 2, page_h - 220, f"Por aprobar satisfactoriamente el programa: {program_title}")
    c.drawCentredString(page_w / 2, page_h - 245, f"Pensum: {curriculum_title}  |  Calificación final: {final_grade}%")

    # Firma y metadatos
    c.setFont("Helvetica-Bold", 11)
    c.drawString(70, 125, signer_name)
    c.setFont("Helvetica", 10)
    c.drawString(70, 108, signer_title)
    c.drawString(70, 82, f"Certificado N.º: {certificate_number}")
    c.drawString(70, 66, f"Emitido (UTC): {issued_at.strftime('%Y-%m-%d %H:%M')}")
    c.setFont("Helvetica", 8)
    c.drawString(70, 48, f"Hash verificación: {verification_hash}")

    # Código QR vectorial
    qr_widget = QrCodeWidget(verification_url)
    bounds = qr_widget.getBounds()
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    size = 110.0
    drawing = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
    drawing.add(qr_widget)
    renderPDF.draw(drawing, c, page_w - 175, 65)

    c.setFont("Helvetica", 8)
    c.drawCentredString(page_w - 120, 52, "Escanea para verificar")

    c.showPage()
    c.save()
    return buf.getvalue()


def _calculate_student_curriculum_grade(
    db: Session,
    *,
    user_id: uuid.UUID,
    curriculum_version_id: uuid.UUID,
    classroom_id: uuid.UUID | None,
) -> Decimal:
    """Calcula la calificación ponderada real del pensum a partir de LessonProgress."""
    units = db.scalars(
        select(CurriculumUnit).where(CurriculumUnit.curriculum_version_id == curriculum_version_id)
    ).all()
    if not units:
        raise ValidationDomainError("El pensum no tiene unidades configuradas")

    total_weight = Decimal("0.00")
    weighted_sum = Decimal("0.00")

    for unit in units:
        lv_ids = db.scalars(
            select(LessonVersion.id)
            .join(Lesson, LessonVersion.lesson_id == Lesson.id)
            .join(Module, Lesson.module_id == Module.id)
            .where(Module.course_id == unit.course_id, LessonVersion.status.in_(["published", "superseded"]))
        ).all()
        if not lv_ids:
            continue

        lp_stmt = select(LessonProgress).where(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_version_id.in_(lv_ids),
            LessonProgress.status == "completed",
        )
        if classroom_id is not None:
            lp_stmt = lp_stmt.where(LessonProgress.classroom_id == classroom_id)
        progress_rows = db.scalars(lp_stmt).all()

        if unit.is_mandatory and not progress_rows:
            raise ValidationDomainError(
                f"El estudiante aún no ha completado las lecciones obligatorias de la unidad '{unit.unit_code}'",
                code="curriculum_incomplete",
            )
        if progress_rows:
            unit_avg = sum((p.best_score_pct for p in progress_rows), Decimal("0.00")) / len(progress_rows)
            weighted_sum += unit_avg * unit.weight
            total_weight += unit.weight

    if total_weight == 0:
        raise ValidationDomainError("No hay progreso completado suficiente para emitir certificado")
    return (weighted_sum / total_weight).quantize(Decimal("0.01"))


def issue_certificate(
    db: Session,
    *,
    organization: Organization,
    signer: User,
    student_email: str,
    curriculum_version_id: uuid.UUID,
    classroom_id: uuid.UUID | None,
    signer_title: str,
) -> Certificate:
    student = db.scalar(
        select(User).where(User.email == student_email.strip().lower(), User.deleted_at.is_(None))
    )
    if not student:
        raise NotFoundError("Estudiante no encontrado")

    member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.user_id == student.id,
            OrganizationMember.deleted_at.is_(None),
            OrganizationMember.status == "active",
        )
    )
    if not member:
        raise ValidationDomainError("El estudiante no pertenece activamente a esta organización")

    cv = db.scalar(
        select(CurriculumVersion).where(
            CurriculumVersion.id == curriculum_version_id,
            CurriculumVersion.organization_id == organization.id,
        )
    )
    if not cv or cv.status != "published":
        raise NotFoundError("Versión de pensum publicada no encontrada en esta organización")

    program = db.scalar(select(Program).where(Program.id == cv.program_id))
    final_grade = _calculate_student_curriculum_grade(
        db, user_id=student.id, curriculum_version_id=cv.id, classroom_id=classroom_id
    )
    if final_grade < cv.passing_score:
        raise ValidationDomainError(
            f"La calificación ({final_grade}%) no alcanza el mínimo aprobatorio ({cv.passing_score}%)",
            code="grade_below_passing_score",
        )

    now = datetime.now(timezone.utc)
    cert_id = uuid.uuid4()
    cert_num = f"{organization.slug.upper()[:8]}-{now.year}-{secrets.token_hex(3).upper()}"
    v_hash = compute_verification_hash(
        certificate_id=cert_id,
        organization_id=organization.id,
        user_id=student.id,
        curriculum_version_id=cv.id,
        issued_at=now,
    )
    sig_hash = compute_signature_hash(
        certificate_number=cert_num,
        verification_hash=v_hash,
        final_grade=final_grade,
        signer_user_id=signer.id,
    )

    cert = Certificate(
        id=cert_id,
        organization_id=organization.id,
        user_id=student.id,
        curriculum_version_id=cv.id,
        classroom_id=classroom_id,
        certificate_number=cert_num,
        verification_hash=v_hash,
        final_grade=final_grade,
        status="pending",
        metadata_snapshot_json={
            "organization_name": organization.name,
            "program_title": program.title if program else cv.title,
            "curriculum_title": cv.title,
            "recipient_name": student.full_name,
            "recipient_initials": mask_recipient_name(student.full_name),
            "signer_name": signer.full_name,
            "signer_title": signer_title.strip(),
        },
        issued_at=now,
    )
    db.add(cert)
    db.flush()

    db.add(
        CertificateSignature(
            certificate_id=cert.id,
            signer_user_id=signer.id,
            signer_name=signer.full_name,
            signer_title=signer_title.strip(),
            signature_hash=sig_hash,
            signed_at=now,
        )
    )
    record_audit_log(
        db,
        action="certificate.issued",
        resource_type="certificate",
        resource_id=cert.id,
        organization_id=organization.id,
        actor_user_id=signer.id,
        details={"certificate_number": cert_num, "final_grade": str(final_grade)},
    )
    db.commit()
    db.refresh(cert)
    return cert


def render_certificate_pdf_job(certificate_id: uuid.UUID, session_factory: sessionmaker[Session]) -> None:
    """Tarea asíncrona en segundo plano que genera PDF + QR y marca el certificado como issued."""
    with session_factory() as db:
        cert = db.scalar(select(Certificate).where(Certificate.id == certificate_id))
        if not cert or cert.status == "revoked":
            return

        snap = cert.metadata_snapshot_json
        verify_url = f"{get_settings().frontend_url}/verificar-certificado/{cert.verification_hash}"
        pdf_bytes = generate_certificate_pdf_bytes(
            organization_name=snap["organization_name"],
            recipient_name=snap["recipient_name"],
            program_title=snap["program_title"],
            curriculum_title=snap["curriculum_title"],
            certificate_number=cert.certificate_number,
            verification_hash=cert.verification_hash,
            final_grade=cert.final_grade,
            issued_at=cert.issued_at or datetime.now(timezone.utc),
            signer_name=snap["signer_name"],
            signer_title=snap["signer_title"],
            verification_url=verify_url,
        )
        key = f"orgs/{cert.organization_id}/{cert.id}.pdf"
        path = get_certificates_storage_root() / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pdf_bytes)

        cert.pdf_storage_key = key
        if cert.status == "pending":
            cert.status = "issued"
        db.commit()


def revoke_certificate(
    db: Session,
    *,
    organization_id: uuid.UUID,
    certificate_id: uuid.UUID,
    actor: User,
    reason: str,
) -> Certificate:
    cert = db.scalar(
        select(Certificate).where(
            Certificate.id == certificate_id,
            Certificate.organization_id == organization_id,
        )
    )
    if not cert:
        raise NotFoundError("Certificado no encontrado en esta organización")
    if cert.status == "revoked":
        raise ValidationDomainError("El certificado ya fue revocado")

    cert.status = "revoked"
    db.add(
        CertificateRevocation(
            certificate_id=cert.id,
            revoked_by=actor.id,
            reason=reason.strip(),
        )
    )
    record_audit_log(
        db,
        action="certificate.revoked",
        resource_type="certificate",
        resource_id=cert.id,
        organization_id=organization_id,
        actor_user_id=actor.id,
        details={"reason": reason.strip()},
    )
    db.commit()
    db.refresh(cert)
    return cert


def verify_certificate_by_hash(db: Session, raw_hash: str) -> PublicCertificateVerificationOut:
    """Verifica autenticidad pública sin exponer datos personales sensibles."""
    normalized = raw_hash.strip().lower()
    if not HASH_HEX_PATTERN.match(normalized):
        raise NotFoundError("Certificado no encontrado")

    cert = db.scalar(select(Certificate).where(Certificate.verification_hash == normalized))
    if not cert:
        raise NotFoundError("Certificado no encontrado")

    snap = cert.metadata_snapshot_json
    rev = db.scalar(select(CertificateRevocation).where(CertificateRevocation.certificate_id == cert.id))
    return PublicCertificateVerificationOut(
        valid=(cert.status == "issued"),
        status=cert.status,
        certificate_number=cert.certificate_number,
        organization_name=snap["organization_name"],
        program_title=snap["program_title"],
        curriculum_title=snap["curriculum_title"],
        recipient_initials=snap["recipient_initials"],
        final_grade=cert.final_grade,
        issued_at=cert.issued_at,
        signer_name=snap["signer_name"],
        signer_title=snap["signer_title"],
        revoked_at=rev.revoked_at if rev else None,
        revocation_reason=rev.reason if rev else None,
    )


def claim_eligible_certificates_for_student(db: Session, *, student: User) -> list[Certificate]:
    """Evalúa aulas activas del estudiante y auto-emite certificados si cumple nota y unidades."""
    memberships = db.execute(
        select(ClassroomMember, Classroom, Organization)
        .join(Classroom, ClassroomMember.classroom_id == Classroom.id)
        .join(Organization, Classroom.organization_id == Organization.id)
        .where(
            ClassroomMember.user_id == student.id,
            ClassroomMember.deleted_at.is_(None),
            Classroom.deleted_at.is_(None),
        )
    ).all()

    newly_issued: list[Certificate] = []
    for _cm, classroom, org in memberships:
        existing = db.scalar(
            select(Certificate).where(
                Certificate.user_id == student.id,
                Certificate.curriculum_version_id == classroom.curriculum_version_id,
                Certificate.status.in_(["pending", "issued"]),
            )
        )
        if existing:
            continue

        cv = db.scalar(
            select(CurriculumVersion).where(
                CurriculumVersion.id == classroom.curriculum_version_id,
                CurriculumVersion.status == "published",
            )
        )
        if not cv:
            continue

        try:
            final_grade = _calculate_student_curriculum_grade(
                db,
                user_id=student.id,
                curriculum_version_id=cv.id,
                classroom_id=classroom.id,
            )
        except ValidationDomainError:
            # fallback sin filtrar classroom_id si completó en estudio vinculado
            try:
                final_grade = _calculate_student_curriculum_grade(
                    db,
                    user_id=student.id,
                    curriculum_version_id=cv.id,
                    classroom_id=None,
                )
            except ValidationDomainError:
                continue

        if final_grade < cv.passing_score:
            continue

        cert = issue_certificate(
            db,
            organization=org,
            signer=student,
            student_email=student.email,
            curriculum_version_id=cv.id,
            classroom_id=classroom.id,
            signer_title="Emisión Automática por Cumplimiento de Pensum",
        )
        newly_issued.append(cert)

    return newly_issued
