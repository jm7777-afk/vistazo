"""Punto de entrada principal de FastAPI para Vistazo LMS."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.observability import ObservabilityMiddleware, metrics_registry
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.modules.certificates.router import public_verify_router


def create_app() -> FastAPI:
    """Construye y configura la instancia FastAPI."""
    settings = get_settings()
    if settings.environment == "production" and settings.jwt_secret_key.startswith("dev-only-insecure"):
        raise RuntimeError("JWT_SECRET_KEY no puede usar el valor por defecto en producción")
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Organization-Id", "X-Request-ID"],
    )

    register_exception_handlers(app)
    app.include_router(api_router)
    app.include_router(public_verify_router)

    @app.get("/health", tags=["health"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "vistazo-lms"}

    @app.get("/health/ready", tags=["health"])
    def readiness_check(db: Session = Depends(get_db)) -> JSONResponse:
        db.execute(text("SELECT 1"))
        return JSONResponse({"status": "ready", "database": "ok"})

    @app.get("/metrics", tags=["observability"], response_class=PlainTextResponse)
    def prometheus_metrics() -> PlainTextResponse:
        return PlainTextResponse(metrics_registry.render_prometheus(), media_type="text/plain; version=0.0.4")

    return app


app = create_app()
