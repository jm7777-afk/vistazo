"""Endpoints de autenticación: registro, login, rotación, logout y perfil."""

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdatePreferencesRequest,
    UserSummary,
    VerifyTokenRequest,
)
from app.modules.auth.service import (
    anonymize_user_account,
    authenticate_user,
    build_user_summary,
    register_user,
    request_password_reset,
    reset_password_with_token,
    revoke_session,
    rotate_refresh_token,
    verify_email_with_token,
    verify_parental_consent_with_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "vistazo_refresh"
CSRF_COOKIE_NAME = "vistazo_csrf"


def _set_auth_cookies(response: Response, raw_refresh: str, csrf_token: str) -> None:
    settings = get_settings()
    max_age = settings.refresh_token_expire_days * 86400
    samesite = settings.cookie_samesite if settings.cookie_samesite in {"lax", "strict", "none"} else "lax"
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=samesite,  # type: ignore[arg-type]
        max_age=max_age,
        path="/api/v1/auth",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=samesite,  # type: ignore[arg-type]
        max_age=max_age,
        path="/",
    )


@router.post("/register", response_model=UserSummary, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> UserSummary:
    user = register_user(db, payload, ip_address=request.client.host if request.client else None)
    return build_user_summary(db, user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("15/minute")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user, access_token, raw_refresh, csrf_token, ttl = authenticate_user(
        db,
        email=payload.email,
        password=payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_auth_cookies(response, raw_refresh, csrf_token)
    return TokenResponse(
        access_token=access_token,
        expires_in_seconds=ttl,
        csrf_token=csrf_token,
        user=build_user_summary(db, user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    vistazo_refresh: str | None = Cookie(default=None),
    vistazo_csrf: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    db: Session = Depends(get_db),
) -> TokenResponse:
    if not vistazo_refresh:
        raise UnauthorizedError("Cookie de sesión ausente")
    if not vistazo_csrf or not x_csrf_token or vistazo_csrf != x_csrf_token:
        raise UnauthorizedError("Validación CSRF fallida", code="csrf_failed")

    user, access_token, new_refresh, csrf_token, ttl = rotate_refresh_token(
        db,
        raw_refresh_token=vistazo_refresh,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_auth_cookies(response, new_refresh, csrf_token)
    return TokenResponse(
        access_token=access_token,
        expires_in_seconds=ttl,
        csrf_token=csrf_token,
        user=build_user_summary(db, user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def logout(
    vistazo_refresh: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Response:
    revoke_session(db, vistazo_refresh)
    res = Response(status_code=status.HTTP_204_NO_CONTENT)
    res.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")
    res.delete_cookie(CSRF_COOKIE_NAME, path="/")
    return res


@router.post("/forgot-password")
@limiter.limit("10/minute")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    request_password_reset(
        db, email=payload.email, ip_address=request.client.host if request.client else None
    )
    return {"message": "Si el correo está registrado, enviaremos instrucciones de recuperación."}


@router.post("/reset-password")
@limiter.limit("10/minute")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    reset_password_with_token(
        db,
        raw_token=payload.token,
        new_password=payload.new_password,
        ip_address=request.client.host if request.client else None,
    )
    return {"message": "Contraseña actualizada correctamente."}


@router.post("/verify-email")
def verify_email(payload: VerifyTokenRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    verify_email_with_token(db, raw_token=payload.token)
    return {"message": "Correo verificado correctamente."}


@router.post("/verify-parental-consent")
def verify_parental_consent(payload: VerifyTokenRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    verify_parental_consent_with_token(db, raw_token=payload.token)
    return {"message": "Autorización parental verificada correctamente."}


@router.get("/me", response_model=UserSummary)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserSummary:
    return build_user_summary(db, current_user)


@router.patch("/me/preferences", response_model=UserSummary)
def update_preferences(
    payload: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSummary:
    if payload.preferred_ui_profile is not None:
        current_user.preferred_ui_profile = payload.preferred_ui_profile
    if payload.daily_goal_minutes is not None:
        current_user.daily_goal_minutes = payload.daily_goal_minutes
    if payload.onboarding_completed is not None:
        current_user.onboarding_completed = payload.onboarding_completed
    db.commit()
    db.refresh(current_user)
    return build_user_summary(db, current_user)


@router.post("/me/anonymize", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def anonymize_me(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    anonymize_user_account(db, current_user, ip_address=request.client.host if request.client else None)
    res = Response(status_code=status.HTTP_204_NO_CONTENT)
    res.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")
    res.delete_cookie(CSRF_COOKIE_NAME, path="/")
    return res


@router.post("/forgot-password")
@limiter.limit("10/minute")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    request_password_reset(
        db, email=payload.email, ip_address=request.client.host if request.client else None
    )
    return {"message": "Si el correo está registrado, enviaremos instrucciones de recuperación."}


@router.post("/reset-password")
@limiter.limit("10/minute")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    reset_password_with_token(
        db,
        raw_token=payload.token,
        new_password=payload.new_password,
        ip_address=request.client.host if request.client else None,
    )
    return {"message": "Contraseña actualizada correctamente."}


@router.post("/verify-email")
def verify_email(payload: VerifyTokenRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    verify_email_with_token(db, raw_token=payload.token)
    return {"message": "Correo verificado correctamente."}


@router.post("/verify-parental-consent")
def verify_parental_consent(payload: VerifyTokenRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    verify_parental_consent_with_token(db, raw_token=payload.token)
    return {"message": "Autorización parental verificada correctamente."}
