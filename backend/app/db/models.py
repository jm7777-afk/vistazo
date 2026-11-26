"""Registro central de todos los modelos ORM para descubrimiento de Alembic."""

from app.modules.audit.models import AuditLog
from app.modules.auth.models import ParentalConsent, User, UserSession
from app.modules.challenges.models import Challenge
from app.modules.courses.models import Course, Lesson, LessonVersion, Module
from app.modules.curriculum.models import (
    Classroom,
    ClassroomMember,
    Competency,
    CurriculumUnit,
    CurriculumVersion,
    InstructorAssignment,
    Program,
)
from app.modules.progress.models import ChallengeAttempt, LessonProgress, StudentCompetency
from app.modules.rbac.models import Permission, Role, RolePermission
from app.modules.tenants.models import Organization, OrganizationMember

__all__ = [
    "AuditLog",
    "Challenge",
    "ChallengeAttempt",
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
    "Module",
    "Organization",
    "OrganizationMember",
    "ParentalConsent",
    "Permission",
    "Program",
    "Role",
    "RolePermission",
    "StudentCompetency",
    "User",
    "UserSession",
]
