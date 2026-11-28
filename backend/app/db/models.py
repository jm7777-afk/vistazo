"""Registro central de todos los modelos ORM para descubrimiento de Alembic."""

from app.modules.ai_assistant.models import AIGenerationJob, AIProviderConfig, AsyncTaskRecord
from app.modules.audit.models import AuditLog
from app.modules.auth.models import (
    EmailVerificationToken,
    ParentalConsent,
    PasswordResetToken,
    User,
    UserSession,
)
from app.modules.billing.models import OrganizationSubscription
from app.modules.challenges.models import Challenge, OpenSubmission, QuestionBankItem
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
from app.modules.live_quiz.models import LiveQuizParticipant, LiveQuizSession
from app.modules.media.models import ChallengeMediaAsset, MediaAsset, StudentLibraryItem
from app.modules.notes.models import StudentNote
from app.modules.notifications.models import PushSubscription
from app.modules.progress.models import ChallengeAttempt, LessonProgress, StudentCompetency
from app.modules.rbac.models import Permission, Role, RolePermission
from app.modules.spaced_repetition.models import ReviewSession, ReviewSessionItem, SpacedRepetitionItem
from app.modules.tenants.models import Organization, OrganizationMember

__all__ = [
    "AIGenerationJob",
    "AIProviderConfig",
    "AsyncTaskRecord",
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
    "EmailVerificationToken",
    "InstructorAssignment",
    "Lesson",
    "LessonProgress",
    "LessonVersion",
    "LiveQuizParticipant",
    "LiveQuizSession",
    "MediaAsset",
    "Module",
    "OpenSubmission",
    "Organization",
    "OrganizationMember",
    "OrganizationSubscription",
    "ParentalConsent",
    "PasswordResetToken",
    "Permission",
    "Program",
    "PushSubscription",
    "QuestionBankItem",
    "ReviewSession",
    "ReviewSessionItem",
    "Role",
    "RolePermission",
    "SpacedRepetitionItem",
    "StudentBadge",
    "StudentCompetency",
    "StudentGamificationProfile",
    "StudentLibraryItem",
    "StudentNote",
    "StudyGuide",
    "User",
    "UserSession",
    "XpTransaction",
]
