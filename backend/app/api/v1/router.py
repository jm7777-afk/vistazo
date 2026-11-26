"""Enrutador principal de la API v1."""

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.challenges.router import router as challenges_router
from app.modules.courses.router import router as courses_router
from app.modules.curriculum.router import router as curriculum_router
from app.modules.progress.router import router as progress_router
from app.modules.tenants.router import router as tenants_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(tenants_router)
api_router.include_router(curriculum_router)
api_router.include_router(courses_router)
api_router.include_router(challenges_router)
api_router.include_router(progress_router)
