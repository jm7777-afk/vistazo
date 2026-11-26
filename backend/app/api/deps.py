"""Dependencias FastAPI de autenticación, contexto multi-tenant y RBAC."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Header, Path, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.modules.audit.service import record_audit_log
from app.modules.auth.models import User
from app.modules.rbac.models import Permission, Role, RolePermission
from app.modules.tenants.models import Organization, OrganizationMember

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TenantContext:
    """Contexto verificado de organización, usuario y permisos efectivos."""

    organization: Organization
    user: User
    role_codes: frozenset[str]
    permissions: frozenset[str]
    is_super_admin: bool

    def has_permission(self, permission_code: str) -> bool:
        return self.is_super_admin or permission_code in self.permissions

    def is_coordinator_or_admin(self) -> bool:
        return self.is_super_admin or "coordinator" in self.role_codes


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Valida el JWT Bearer y devuelve el usuario activo."""
    if not credentials or not credentials.credentials:
        raise UnauthorizedError("Token Bearer requerido")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, KeyError) as exc:
        raise UnauthorizedError("Token de acceso inválido o expirado") from exc

    user = db.scalar(
        select(User).where(User.id == user_id, User.deleted_at.is_(None), User.is_active.is_(True))
    )
    if not user:
        raise UnauthorizedError("Usuario inactivo o inexistente")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Devuelve el usuario si envía token válido, o None para navegación pública."""
    if not credentials or not credentials.credentials:
        return None
    return get_current_user(credentials=credentials, db=db)


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Exige privilegios globales de SuperAdministrador."""
    if not current_user.is_super_admin:
        raise ForbiddenError("Se requiere rol de SuperAdministrador")
    return current_user


def get_tenant_context(
    request: Request,
    org_id: uuid.UUID = Path(..., description="Identificador de la organización"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantContext:
    """Valida existencia del tenant y membresía activa del usuario en backend."""
    org = db.scalar(
        select(Organization).where(
            Organization.id == org_id,
            Organization.deleted_at.is_(None),
            Organization.is_active.is_(True),
        )
    )
    if not org:
        raise NotFoundError("Organización no encontrada")

    if current_user.is_super_admin:
        all_perms = db.scalars(select(Permission.code)).all()
        return TenantContext(
            organization=org,
            user=current_user,
            role_codes=frozenset({"super_admin"}),
            permissions=frozenset(all_perms),
            is_super_admin=True,
        )

    memberships = db.execute(
        select(OrganizationMember, Role)
        .join(Role, OrganizationMember.role_id == Role.id)
        .where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.deleted_at.is_(None),
            OrganizationMember.status == "active",
            Role.deleted_at.is_(None),
        )
    ).all()

    if not memberships:
        record_audit_log(
            db,
            action="tenant.access_denied",
            resource_type="organization",
            resource_id=org.id,
            organization_id=org.id,
            actor_user_id=current_user.id,
            outcome="denied",
            ip_address=request.client.host if request.client else None,
            details={"path": str(request.url.path)},
        )
        db.commit()
        raise ForbiddenError("No perteneces a esta organización")

    role_ids = [role.id for _member, role in memberships]
    role_codes = frozenset(role.code for _member, role in memberships)
    perm_codes = db.scalars(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id.in_(role_ids))
    ).all()

    return TenantContext(
        organization=org,
        user=current_user,
        role_codes=role_codes,
        permissions=frozenset(perm_codes),
        is_super_admin=False,
    )


def require_permission(permission_code: str) -> Callable[..., TenantContext]:
    """Genera una dependencia FastAPI que verifica un permiso granular en el tenant."""

    def _dependency(
        request: Request,
        tenant: TenantContext = Depends(get_tenant_context),
        db: Session = Depends(get_db),
    ) -> TenantContext:
        if not tenant.has_permission(permission_code):
            record_audit_log(
                db,
                action="rbac.permission_denied",
                resource_type="permission",
                organization_id=tenant.organization.id,
                actor_user_id=tenant.user.id,
                outcome="denied",
                ip_address=request.client.host if request.client else None,
                details={"required_permission": permission_code, "path": str(request.url.path)},
            )
            db.commit()
            raise ForbiddenError(f"Permiso requerido: {permission_code}")
        return tenant

    return _dependency


def get_optional_org_header(
    x_organization_id: uuid.UUID | None = Header(default=None, alias="X-Organization-Id"),
) -> uuid.UUID | None:
    """Lee cabecera opcional de organización para contextos mixtos."""
    return x_organization_id
