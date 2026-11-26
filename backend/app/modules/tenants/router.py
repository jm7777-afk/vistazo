"""Endpoints multi-tenant para administración de organizaciones y membresías."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, require_permission, require_super_admin
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.db.session import get_db
from app.modules.audit.models import AuditLog
from app.modules.audit.service import record_audit_log
from app.modules.auth.models import User
from app.modules.curriculum.models import CurriculumVersion, Program
from app.modules.rbac.models import Role
from app.modules.tenants.models import Organization, OrganizationMember
from app.modules.tenants.schemas import (
    AddMemberRequest,
    AuditLogOut,
    OrganizationCreate,
    OrganizationMemberOut,
    OrganizationOnboardOut,
    OrganizationOnboardRequest,
    OrganizationOut,
)

router = APIRouter(tags=["tenants"])


@router.get("/admin/organizations", response_model=list[OrganizationOut])
def list_all_organizations(
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[OrganizationOut]:
    orgs = db.scalars(
        select(Organization).where(Organization.deleted_at.is_(None)).order_by(Organization.created_at.desc())
    ).all()
    return [
        OrganizationOut(
            id=o.id,
            name=o.name,
            slug=o.slug,
            sector_type=o.sector_type,
            default_ui_profile=o.default_ui_profile,
            is_active=o.is_active,
            created_at=o.created_at,
        )
        for o in orgs
    ]


@router.post("/admin/organizations", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> OrganizationOut:
    existing = db.scalar(
        select(Organization).where(Organization.slug == payload.slug.lower(), Organization.deleted_at.is_(None))
    )
    if existing:
        raise ConflictError("El slug organizacional ya existe")

    org = Organization(
        name=payload.name.strip(),
        slug=payload.slug.lower(),
        sector_type=payload.sector_type,
        default_ui_profile=payload.default_ui_profile,
        settings_json=payload.settings_json,
    )
    db.add(org)
    db.flush()
    record_audit_log(
        db,
        action="organization.created",
        resource_type="organization",
        resource_id=org.id,
        organization_id=org.id,
        actor_user_id=admin.id,
    )
    db.commit()
    db.refresh(org)
    return OrganizationOut(
        id=org.id,
        name=org.name,
        slug=org.slug,
        sector_type=org.sector_type,
        default_ui_profile=org.default_ui_profile,
        is_active=org.is_active,
        created_at=org.created_at,
    )


@router.post("/admin/organizations/onboard", response_model=OrganizationOnboardOut, status_code=status.HTTP_201_CREATED)
def onboard_organization(
    payload: OrganizationOnboardRequest,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> OrganizationOnboardOut:
    """Onboarding atómico de nueva institución: organización, coordinador, programa y pensum v1."""
    existing = db.scalar(
        select(Organization).where(Organization.slug == payload.slug.lower(), Organization.deleted_at.is_(None))
    )
    if existing:
        raise ConflictError("El slug organizacional ya existe")

    coord_role = db.scalar(
        select(Role).where(Role.code == "coordinator", Role.organization_id.is_(None), Role.deleted_at.is_(None))
    )
    if not coord_role:
        raise NotFoundError("Rol coordinador del sistema no encontrado")

    org = Organization(
        name=payload.name.strip(),
        slug=payload.slug.lower(),
        sector_type=payload.sector_type,
        default_ui_profile=payload.default_ui_profile,
    )
    db.add(org)
    db.flush()

    coord_email = payload.coordinator_email.strip().lower()
    coord_user = db.scalar(select(User).where(User.email == coord_email, User.deleted_at.is_(None)))
    if not coord_user:
        coord_user = User(
            email=coord_email,
            password_hash=hash_password(payload.coordinator_password),
            full_name=payload.coordinator_name.strip(),
            preferred_ui_profile=payload.default_ui_profile,
        )
        db.add(coord_user)
        db.flush()

    db.add(OrganizationMember(organization_id=org.id, user_id=coord_user.id, role_id=coord_role.id))

    program = Program(
        organization_id=org.id,
        code=payload.initial_program_code.strip(),
        title=payload.initial_program_title.strip(),
        education_level=payload.education_level,
    )
    db.add(program)
    db.flush()

    cv = CurriculumVersion(
        organization_id=org.id,
        program_id=program.id,
        version_number=1,
        title=f"{program.title} — Pensum v1",
        created_by=coord_user.id,
        status="draft",
    )
    db.add(cv)
    db.flush()

    record_audit_log(
        db,
        action="organization.onboarded",
        resource_type="organization",
        resource_id=org.id,
        organization_id=org.id,
        actor_user_id=admin.id,
        details={"coordinator_email": coord_email, "program_code": program.code},
    )
    db.commit()
    db.refresh(org)

    return OrganizationOnboardOut(
        organization=OrganizationOut(
            id=org.id,
            name=org.name,
            slug=org.slug,
            sector_type=org.sector_type,
            default_ui_profile=org.default_ui_profile,
            is_active=org.is_active,
            created_at=org.created_at,
        ),
        coordinator_user_id=coord_user.id,
        program_id=program.id,
        curriculum_version_id=cv.id,
    )


@router.get("/orgs/{org_id}/members", response_model=list[OrganizationMemberOut])
def list_org_members(
    tenant: TenantContext = Depends(require_permission("org:manage")),
    db: Session = Depends(get_db),
) -> list[OrganizationMemberOut]:
    rows = db.execute(
        select(OrganizationMember, User, Role)
        .join(User, OrganizationMember.user_id == User.id)
        .join(Role, OrganizationMember.role_id == Role.id)
        .where(
            OrganizationMember.organization_id == tenant.organization.id,
            OrganizationMember.deleted_at.is_(None),
            User.deleted_at.is_(None),
        )
        .order_by(OrganizationMember.joined_at.desc())
    ).all()
    return [
        OrganizationMemberOut(
            membership_id=m.id,
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            role_code=r.code,
            role_name=r.name,
            status=m.status,
            joined_at=m.joined_at,
        )
        for m, u, r in rows
    ]


@router.post("/orgs/{org_id}/members", response_model=OrganizationMemberOut, status_code=status.HTTP_201_CREATED)
def add_org_member(
    payload: AddMemberRequest,
    tenant: TenantContext = Depends(require_permission("org:manage")),
    db: Session = Depends(get_db),
) -> OrganizationMemberOut:
    user = db.scalar(
        select(User).where(User.email == payload.user_email.lower(), User.deleted_at.is_(None))
    )
    if not user:
        raise NotFoundError("Usuario no encontrado para afiliación")

    role = db.scalar(
        select(Role).where(
            Role.code == payload.role_code,
            Role.organization_id.is_(None),
            Role.deleted_at.is_(None),
        )
    )
    if not role:
        raise NotFoundError("Rol no disponible")

    existing = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == tenant.organization.id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.role_id == role.id,
            OrganizationMember.deleted_at.is_(None),
        )
    )
    if existing:
        raise ConflictError("El usuario ya posee ese rol en esta organización")

    member = OrganizationMember(
        organization_id=tenant.organization.id,
        user_id=user.id,
        role_id=role.id,
    )
    db.add(member)
    db.flush()
    record_audit_log(
        db,
        action="organization.member_added",
        resource_type="organization_member",
        resource_id=member.id,
        organization_id=tenant.organization.id,
        actor_user_id=tenant.user.id,
        details={"target_user_id": str(user.id), "role_code": role.code},
    )
    db.commit()
    return OrganizationMemberOut(
        membership_id=member.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role_code=role.code,
        role_name=role.name,
        status=member.status,
        joined_at=member.joined_at,
    )


@router.delete("/orgs/{org_id}/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def remove_org_member(
    membership_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("org:manage")),
    db: Session = Depends(get_db),
) -> Response:
    member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.id == membership_id,
            OrganizationMember.organization_id == tenant.organization.id,
            OrganizationMember.deleted_at.is_(None),
        )
    )
    if not member:
        raise NotFoundError("Membresía no encontrada en esta organización")

    member.deleted_at = datetime.now(timezone.utc)
    member.deleted_by = tenant.user.id
    record_audit_log(
        db,
        action="organization.member_removed",
        resource_type="organization_member",
        resource_id=member.id,
        organization_id=tenant.organization.id,
        actor_user_id=tenant.user.id,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/orgs/{org_id}/audit-logs", response_model=list[AuditLogOut])
def list_org_audit_logs(
    tenant: TenantContext = Depends(require_permission("org:manage")),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == tenant.organization.id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    ).all()
    return [
        AuditLogOut(
            id=item.id,
            organization_id=item.organization_id,
            actor_user_id=item.actor_user_id,
            action=item.action,
            resource_type=item.resource_type,
            resource_id=item.resource_id,
            outcome=item.outcome,
            details_json=item.details_json,
            created_at=item.created_at,
        )
        for item in logs
    ]


@router.get("/admin/audit-logs", response_model=list[AuditLogOut])
def list_global_audit_logs(
    _admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    logs = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)).all()
    return [
        AuditLogOut(
            id=item.id,
            organization_id=item.organization_id,
            actor_user_id=item.actor_user_id,
            action=item.action,
            resource_type=item.resource_type,
            resource_id=item.resource_id,
            outcome=item.outcome,
            details_json=item.details_json,
            created_at=item.created_at,
        )
        for item in logs
    ]
