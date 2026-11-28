"""Enrutador principal de la API v1."""

from fastapi import APIRouter

from app.modules.ai_assistant.router import router as ai_router
from app.modules.analytics.router import router as analytics_router
from app.modules.auth.router import router as auth_router
from app.modules.billing.router import router as billing_router
from app.modules.certificates.router import router as certificates_router
from app.modules.challenges.router import router as challenges_router
from app.modules.courses.router import router as courses_router
from app.modules.curriculum.router import public_router as public_curriculum_router
from app.modules.curriculum.router import router as curriculum_router
from app.modules.gamification.router import router as gamification_router
from app.modules.live_quiz.router import router as live_quiz_router
from app.modules.media.router import router as media_router
from app.modules.notes.router import router as notes_router
from app.modules.notifications.router import router as notifications_router
from app.modules.progress.router import router as progress_router
from app.modules.spaced_repetition.router import router as spaced_repetition_router
from app.modules.tenants.router import router as tenants_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(tenants_router)
api_router.include_router(curriculum_router)
api_router.include_router(public_curriculum_router)
api_router.include_router(courses_router)
api_router.include_router(challenges_router)
api_router.include_router(progress_router)
api_router.include_router(spaced_repetition_router)
api_router.include_router(media_router)
api_router.include_router(gamification_router)
api_router.include_router(analytics_router)
api_router.include_router(ai_router)
api_router.include_router(certificates_router)
api_router.include_router(live_quiz_router)
api_router.include_router(notifications_router)
api_router.include_router(notes_router)
api_router.include_router(billing_router)
