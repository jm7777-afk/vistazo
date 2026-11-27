"""Servicios de registro, login, rotación de refresh tokens y perfil."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationDomainError
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.audit.service import record_audit_log
from app.modules.auth.models import ParentalConsent, User, UserSession
from app.modules.auth.schemas import MembershipSummary, RegisterRequest, UserSummary
from app.modules.rbac.models import Role
from app.modules.tenants.models import Organization, OrganizationMember


def _is_minor_birth_date(birth_date: date | None) -> bool:
    if not birth_date:
        return False
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age < 14


def _ensure_aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def build_user_summary(db: Session, user: User) -> UserSummary:
    """Construye el resumen del usuario con sus membresías organizacionales activas."""
    rows = db.execute(
        select(Organization, Role)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .join(Role, OrganizationMember.role_id == Role.id)
        .where(
            OrganizationMember.user_id == user.id,
            OrganizationMember.deleted_at.is_(None),
            OrganizationMember.status == "active",
            Organization.deleted_at.is_(None),
            Organization.is_active.is_(True),
        )
    ).all()

    memberships = [
        MembershipSummary(
            organization_id=org.id,
            organization_name=org.name,
            organization_slug=org.slug,
            sector_type=org.sector_type,
            default_ui_profile=org.default_ui_profile,
            role_code=role.code,
            role_name=role.name,
        )
        for org, role in rows
    ]

    return UserSummary(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_minor=user.is_minor,
        preferred_ui_profile=user.preferred_ui_profile,
        daily_goal_minutes=user.daily_goal_minutes,
        onboarding_completed=user.onboarding_completed,
        is_super_admin=user.is_super_admin,
        created_at=user.created_at,
        memberships=memberships,
    )


def register_user(db: Session, data: RegisterRequest, ip_address: str | None) -> User:
    """Registra un usuario nuevo validando unicidad y consentimiento si es menor."""
    normalized_email = data.email.strip().lower()
    existing = db.scalar(
        select(User).where(User.email == normalized_email, User.deleted_at.is_(None))
    )
    if existing:
        raise ConflictError("El correo electrónico ya está registrado")

    is_minor = _is_minor_birth_date(data.birth_date)
    if is_minor and (not data.guardian_name or not data.guardian_email):
        raise ValidationDomainError(
            "El registro de menores requiere nombre y correo del representante legal",
            code="parental_consent_required",
        )

    user = User(
        email=normalized_email,
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip(),
        birth_date=data.birth_date,
        is_minor=is_minor,
        preferred_ui_profile=data.preferred_ui_profile,
    )
    db.add(user)
    db.flush()

    if is_minor:
        consent = ParentalConsent(
            minor_user_id=user.id,
            guardian_name=data.guardian_name.strip(),  # type: ignore[union-attr]
            guardian_email=str(data.guardian_email).lower(),
            consent_status="pending",
            verification_token_hash=hash_token(generate_opaque_token()),
        )
        db.add(consent)

    record_audit_log(
        db,
        action="auth.register",
        resource_type="user",
        resource_id=user.id,
        actor_user_id=user.id,
        ip_address=ip_address,
        details={"is_minor": is_minor},
    )
    db.commit()
    db.refresh(user)
    return user


def issue_session_tokens(
    db: Session,
    user: User,
    *,
    ip_address: str | None,
    user_agent: str | None,
    family_id: uuid.UUID | None = None,
) -> tuple[str, str, str, int]:
    """Emite JWT de acceso, refresh token opaco persistido y CSRF token."""
    settings = get_settings()
    raw_refresh = generate_opaque_token()
    csrf_token = generate_opaque_token()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)

    session_row = UserSession(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        family_id=family_id or uuid.uuid4(),
        user_agent=user_agent[:512] if user_agent else None,
        ip_address=ip_address,
        expires_at=expires_at,
    )
    db.add(session_row)

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"is_super_admin": user.is_super_admin},
    )
    return access_token, raw_refresh, csrf_token, settings.access_token_expire_minutes * 60


def authenticate_user(
    db: Session,
    *,
    email: str,
    password: str,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[User, str, str, str, int]:
    """Autentica credenciales y abre familia de sesión."""
    normalized_email = email.strip().lower()
    user = db.scalar(
        select(User).where(User.email == normalized_email, User.deleted_at.is_(None))
    )
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        record_audit_log(
            db,
            action="auth.login_failed",
            resource_type="user",
            actor_user_id=user.id if user else None,
            outcome="denied",
            ip_address=ip_address,
        )
        db.commit()
        raise UnauthorizedError("Credenciales inválidas")

    user.last_login_at = datetime.now(timezone.utc)
    access_token, raw_refresh, csrf_token, ttl = issue_session_tokens(
        db, user, ip_address=ip_address, user_agent=user_agent
    )
    record_audit_log(
        db,
        action="auth.login_success",
        resource_type="user",
        resource_id=user.id,
        actor_user_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
    return user, access_token, raw_refresh, csrf_token, ttl


def rotate_refresh_token(
    db: Session,
    *,
    raw_refresh_token: str,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[User, str, str, str, int]:
    """Rota el refresh token y revoca toda la familia ante detección de reuso."""
    token_digest = hash_token(raw_refresh_token)
    session_row = db.scalar(select(UserSession).where(UserSession.token_hash == token_digest))
    now = datetime.now(timezone.utc)

    if not session_row:
        raise UnauthorizedError("Sesión de renovación inválida")

    if session_row.revoked_at is not None:
        # Detección de reuso: revoca toda la familia inmediatamente
        db.execute(
            update(UserSession)
            .where(UserSession.family_id == session_row.family_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        record_audit_log(
            db,
            action="auth.refresh_reuse_detected",
            resource_type="user_session",
            resource_id=session_row.id,
            actor_user_id=session_row.user_id,
            outcome="denied",
            ip_address=ip_address,
        )
        db.commit()
        raise UnauthorizedError("Sesión comprometida; inicia sesión nuevamente")

    if _ensure_aware_utc(session_row.expires_at) <= now:
        session_row.revoked_at = now
        db.commit()
        raise UnauthorizedError("Sesión expirada")

    user = db.scalar(
        select(User).where(User.id == session_row.user_id, User.deleted_at.is_(None), User.is_active.is_(True))
    )
    if not user:
        raise UnauthorizedError("Usuario inactivo")

    session_row.revoked_at = now
    access_token, new_refresh, csrf_token, ttl = issue_session_tokens(
        db, user, ip_address=ip_address, user_agent=user_agent, family_id=session_row.family_id
    )
    db.commit()
    return user, access_token, new_refresh, csrf_token, ttl


def revoke_session(db: Session, raw_refresh_token: str | None) -> None:
    """Revoca la sesión asociada al refresh token."""
    if not raw_refresh_token:
        return
    token_digest = hash_token(raw_refresh_token)
    session_row = db.scalar(select(UserSession).where(UserSession.token_hash == token_digest))
    if session_row and session_row.revoked_at is None:
        session_row.revoked_at = datetime.now(timezone.utc)
        db.commit()


def anonymize_user_account(db: Session, user: User, ip_address: str | None) -> None:
    """Anonimiza PII del usuario conservando integridad referencial histórica y auditoría."""
    now = datetime.now(timezone.utc)
    user.email = f"anonymized-{user.id}@redacted.invalid"
    user.full_name = "Usuario Anonimizado"
    user.birth_date = None
    user.is_active = False
    user.deleted_at = now
    user.deleted_by = user.id

    db.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    record_audit_log(
        db,
        action="auth.account_anonymized",
        resource_type="user",
        resource_id=user.id,
        actor_user_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
