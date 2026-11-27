"""Registro central de todos los modelos ORM para descubrimiento de Alembic."""

from app.modules.ai_assistant.models import AIGenerationJob, AIProviderConfig
from app.modules.audit.models import AuditLog
from app.modules.auth.models import ParentalConsent, User, UserSession
from app.modules.challenges.models import Challenge
from app.modules.certificates.models import Certificate, CertificateRevocation, CertificateSignature
from app.modules.courses.models import Course, Lesson, LessonVersion, Module, StudyGuide
from app.modules.curriculum.models import (
    Classroom,
    ClassroomMember,
    Competency,
    CurriculumUnit,
    CurriculumVersion,
    InstructorAssignment,
    Program,
)
from app.modules.gamification.models import Badge, StudentBadge, StudentGamificationProfile, XpTransaction
from app.modules.media.models import ChallengeMediaAsset, MediaAsset, StudentLibraryItem
from app.modules.progress.models import ChallengeAttempt, LessonProgress, StudentCompetency
from app.modules.rbac.models import Permission, Role, RolePermission
from app.modules.spaced_repetition.models import ReviewSession, ReviewSessionItem, SpacedRepetitionItem
from app.modules.tenants.models import Organization, OrganizationMember

__all__ = [
    "AIGenerationJob",
    "AIProviderConfig",
    "AuditLog",
    "Badge",
    "Certificate",
    "CertificateRevocation",
    "CertificateSignature",
    "Challenge",
    "ChallengeAttempt",
    "ChallengeMediaAsset",
    "Classroom",
    "ClassroomMember",
    "Competency",
    "Course",
    "CurriculumUnit",
    "CurriculumVersion",
    "InstructorAssignment",
    "Lesson",
    "LessonProgress",
    "LessonVersion",
    "MediaAsset",
    "Module",
    "Organization",
    "OrganizationMember",
    "ParentalConsent",
    "Permission",
    "Program",
    "ReviewSession",
    "ReviewSessionItem",
    "Role",
    "RolePermission",
    "SpacedRepetitionItem",
    "StudentBadge",
    "StudentCompetency",
    "StudentGamificationProfile",
    "StudentLibraryItem",
    "StudyGuide",
    "User",
    "UserSession",
    "XpTransaction",
]
