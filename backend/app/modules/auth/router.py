"""Endpoints de autenticación: registro, login, rotación, logout y perfil."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserSummary
from app.modules.auth.service import (
    anonymize_user_account,
    authenticate_user,
    build_user_summary,
    register_user,
    revoke_session,
    rotate_refresh_token,
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
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> UserSummary:
    user = register_user(db, payload, ip_address=request.client.host if request.client else None)
    return build_user_summary(db, user)


@router.post("/login", response_model=TokenResponse)
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


@router.get("/me", response_model=UserSummary)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserSummary:
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
