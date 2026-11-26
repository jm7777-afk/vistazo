"""Endpoints institucionales, personales y ruta pública de verificación de certificados."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import TenantContext, get_current_user, require_permission
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db, get_session_factory
from app.modules.auth.models import User
from app.modules.certificates.models import Certificate
from app.modules.certificates.schemas import (
    CertificateOut,
    IssueCertificateRequest,
    PublicCertificateVerificationOut,
    RevokeCertificateRequest,
)
from app.modules.certificates.service import (
    check_verify_rate_limit,
    get_certificates_storage_root,
    issue_certificate,
    revoke_certificate,
    verify_certificate_by_hash,
)
from app.modules.tenants.models import OrganizationMember
from app.workers.tasks import dispatch_certificate_pdf

router = APIRouter(tags=["certificates"])
public_verify_router = APIRouter(tags=["certificates_public"])


def _to_out(c: Certificate) -> CertificateOut:
    return CertificateOut(
        id=c.id,
        organization_id=c.organization_id,
        user_id=c.user_id,
        curriculum_version_id=c.curriculum_version_id,
        classroom_id=c.classroom_id,
        certificate_number=c.certificate_number,
        verification_hash=c.verification_hash,
        final_grade=c.final_grade,
        status=c.status,
        issued_at=c.issued_at,
        verification_url=f"/verificar-certificado/{c.verification_hash}",
        has_pdf=bool(c.pdf_storage_key),
    )


@router.post("/orgs/{org_id}/certificates/issue", response_model=CertificateOut, status_code=status.HTTP_201_CREATED)
def issue_org_certificate(
    payload: IssueCertificateRequest,
    background_tasks: BackgroundTasks,
    tenant: TenantContext = Depends(require_permission("certificate:issue")),
    db: Session = Depends(get_db),
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
) -> CertificateOut:
    cert = issue_certificate(
        db,
        organization=tenant.organization,
        signer=tenant.user,
        student_email=payload.student_email,
        curriculum_version_id=payload.curriculum_version_id,
        classroom_id=payload.classroom_id,
        signer_title=payload.signer_title,
    )
    dispatch_certificate_pdf(
        certificate_id=cert.id,
        background_tasks=background_tasks,
        session_factory=session_factory,
    )
    return _to_out(cert)


@router.get("/orgs/{org_id}/certificates", response_model=list[CertificateOut])
def list_org_certificates(
    tenant: TenantContext = Depends(require_permission("certificate:issue")),
    db: Session = Depends(get_db),
) -> list[CertificateOut]:
    certs = db.scalars(
        select(Certificate)
        .where(Certificate.organization_id == tenant.organization.id)
        .order_by(Certificate.created_at.desc())
    ).all()
    return [_to_out(c) for c in certs]


@router.post("/orgs/{org_id}/certificates/{certificate_id}/revoke", response_model=CertificateOut)
def revoke_org_certificate(
    certificate_id: uuid.UUID,
    payload: RevokeCertificateRequest,
    tenant: TenantContext = Depends(require_permission("certificate:issue")),
    db: Session = Depends(get_db),
) -> CertificateOut:
    cert = revoke_certificate(
        db,
        organization_id=tenant.organization.id,
        certificate_id=certificate_id,
        actor=tenant.user,
        reason=payload.reason,
    )
    return _to_out(cert)


@router.get("/certificates/me", response_model=list[CertificateOut])
def list_my_certificates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CertificateOut]:
    certs = db.scalars(
        select(Certificate)
        .where(Certificate.user_id == current_user.id)
        .order_by(Certificate.created_at.desc())
    ).all()
    return [_to_out(c) for c in certs]


@router.get("/certificates/{certificate_id}/pdf")
def download_certificate_pdf(
    certificate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    cert = db.scalar(select(Certificate).where(Certificate.id == certificate_id))
    if not cert:
        raise NotFoundError("Certificado no encontrado")

    if cert.user_id != current_user.id and not current_user.is_super_admin:
        member = db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == cert.organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.deleted_at.is_(None),
                OrganizationMember.status == "active",
            )
        )
        if not member:
            raise ForbiddenError("No tienes permiso para descargar este certificado")

    if not cert.pdf_storage_key:
        raise NotFoundError("El PDF aún está en generación asíncrona")

    pdf_path = get_certificates_storage_root() / cert.pdf_storage_key
    if not pdf_path.exists():
        raise NotFoundError("Archivo PDF no disponible")

    return Response(
        content=pdf_path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{cert.certificate_number}.pdf"'},
    )


@public_verify_router.get("/verificar-certificado/{cert_hash}", response_model=PublicCertificateVerificationOut)
@router.get("/verificar-certificado/{cert_hash}", response_model=PublicCertificateVerificationOut)
def verify_certificate_public(
    cert_hash: str,
    request: Request,
    db: Session = Depends(get_db),
) -> PublicCertificateVerificationOut:
    client_ip = request.client.host if request.client else "unknown"
    check_verify_rate_limit(client_ip)
    return verify_certificate_by_hash(db, cert_hash)
