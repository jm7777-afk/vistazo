"""Configuración central de la aplicación cargada desde variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_origins(value: str | None) -> list[str]:
    if not value:
        return ["http://localhost:5173"]
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Parámetros inmutables de configuración del backend."""

    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Vistazo LMS API"))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "sqlite:///./vistazo_dev.db",
        )
    )
    jwt_secret_key: str = field(
        default_factory=lambda: os.getenv(
            "JWT_SECRET_KEY",
            "dev-only-insecure-secret-change-in-production-32chars",
        )
    )
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    access_token_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    )
    refresh_token_expire_days: int = field(
        default_factory=lambda: int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))
    )
    cookie_secure: bool = field(
        default_factory=lambda: _parse_bool(os.getenv("COOKIE_SECURE"), default=False)
    )
    cors_origins: list[str] = field(
        default_factory=lambda: _parse_origins(os.getenv("CORS_ORIGINS"))
    )
    ai_provider: str = field(default_factory=lambda: os.getenv("AI_PROVIDER", "fallback"))
    gemini_api_key: str | None = field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or None)
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
    groq_api_key: str | None = field(default_factory=lambda: os.getenv("GROQ_API_KEY") or None)
    groq_model: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
    ai_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("AI_TIMEOUT_SECONDS", "20")))
    ai_max_tokens: int = field(default_factory=lambda: int(os.getenv("AI_MAX_TOKENS", "2500")))
    ai_daily_org_job_limit: int = field(default_factory=lambda: int(os.getenv("AI_DAILY_ORG_JOB_LIMIT", "50")))
    redis_url: str | None = field(default_factory=lambda: os.getenv("REDIS_URL") or None)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve instancia cacheada de configuración."""
    return Settings()
