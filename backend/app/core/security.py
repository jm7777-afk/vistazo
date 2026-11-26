"""Utilidades criptográficas, hashing de contraseñas, JWT y tokens opacos."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings


def hash_password(plain_password: str) -> str:
    """Genera un hash seguro usando bcrypt (o Argon2id cuando está instalado)."""
    try:
        from argon2 import PasswordHasher  # type: ignore

        return PasswordHasher().hash(plain_password)
    except ImportError:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verifica contraseña en tiempo constante compatible con Argon2id y bcrypt."""
    if password_hash.startswith("$argon2"):
        try:
            from argon2 import PasswordHasher  # type: ignore

            return PasswordHasher().verify(password_hash, plain_password)
        except Exception:
            return False
    if password_hash.startswith("$2"):
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError:
            return False
    return False


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Genera un JWT de acceso de corta duración."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(12),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica y valida un JWT de acceso."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Token inválido o expirado") from exc
    if payload.get("type") != "access" or not payload.get("sub"):
        raise ValueError("Tipo de token inválido")
    return payload


def generate_opaque_token() -> str:
    """Genera un token aleatorio criptográfico para refresh tokens o CSRF."""
    return secrets.token_urlsafe(48)


def hash_token(raw_token: str) -> str:
    """Calcula SHA-256 hexadecimal de un token opaco antes de persistirlo."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
