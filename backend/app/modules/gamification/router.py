"""Endpoints de gamificación (perfil XP/rachas/energía, insignias y ranking por aula)."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_current_user, get_tenant_context
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.curriculum.models import Classroom, ClassroomMember, InstructorAssignment
from app.modules.gamification.models import Badge, StudentBadge, XpTransaction
from app.modules.gamification.service import get_or_create_profile

router = APIRouter(tags=["gamification"])


class BadgeOut(BaseModel):
    code: str
    name: str
    description: str
    awarded_at: datetime


class GamificationProfileOut(BaseModel):
    total_xp: int
    current_streak_days: int
    longest_streak_days: int
    current_energy: int
    max_energy: int
    badges: list[BadgeOut]


class LeaderboardEntryOut(BaseModel):
    rank: int
    display_name: str
    xp_in_classroom: int
    is_me: bool


@router.get("/gamification/me", response_model=GamificationProfileOut)
def my_gamification_profile(
    organization_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GamificationProfileOut:
    profile = get_or_create_profile(db, user_id=current_user.id, organization_id=organization_id)
    db.commit()

    badge_rows = db.execute(
        select(StudentBadge, Badge)
        .join(Badge, StudentBadge.badge_id == Badge.id)
        .where(StudentBadge.user_id == current_user.id)
        .order_by(StudentBadge.awarded_at.desc())
    ).all()

    return GamificationProfileOut(
        total_xp=profile.total_xp,
        current_streak_days=profile.current_streak_days,
        longest_streak_days=profile.longest_streak_days,
        current_energy=profile.current_energy,
        max_energy=profile.max_energy,
        badges=[
            BadgeOut(
                code=b.code,
                name=b.name,
                description=b.description,
                awarded_at=sb.awarded_at,
            )
            for sb, b in badge_rows
        ],
    )


@router.get("/orgs/{org_id}/classrooms/{classroom_id}/leaderboard", response_model=list[LeaderboardEntryOut])
def classroom_leaderboard(
    classroom_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> list[LeaderboardEntryOut]:
    classroom = db.scalar(
        select(Classroom).where(
            Classroom.id == classroom_id,
            Classroom.organization_id == tenant.organization.id,
            Classroom.deleted_at.is_(None),
        )
    )
    if not classroom:
        raise NotFoundError("Aula no encontrada")

    # Solo miembros del aula, instructor asignado o coordinador
    if not tenant.has_permission("classroom:manage"):
        is_inst = db.scalar(
            select(InstructorAssignment).where(
                InstructorAssignment.classroom_id == classroom.id,
                InstructorAssignment.instructor_user_id == tenant.user.id,
                InstructorAssignment.deleted_at.is_(None),
            )
        )
        is_member = db.scalar(
            select(ClassroomMember).where(
                ClassroomMember.classroom_id == classroom.id,
                ClassroomMember.user_id == tenant.user.id,
                ClassroomMember.deleted_at.is_(None),
            )
        )
        if not is_inst and not is_member:
            raise ForbiddenError("No perteneces a esta aula")

    xp_subq = (
        select(XpTransaction.user_id, func.coalesce(func.sum(XpTransaction.xp_amount), 0).label("xp"))
        .where(XpTransaction.classroom_id == classroom.id)
        .group_by(XpTransaction.user_id)
        .subquery()
    )

    rows = db.execute(
        select(User, func.coalesce(xp_subq.c.xp, 0).label("xp"))
        .join(ClassroomMember, ClassroomMember.user_id == User.id)
        .outerjoin(xp_subq, xp_subq.c.user_id == User.id)
        .where(
            ClassroomMember.classroom_id == classroom.id,
            ClassroomMember.deleted_at.is_(None),
            User.deleted_at.is_(None),
        )
        .order_by(desc("xp"), User.full_name.asc())
    ).all()

    def _safe_name(u: User) -> str:
        if u.is_minor and u.id != tenant.user.id:
            parts = u.full_name.split()
            return " ".join(f"{p[0]}." for p in parts if p) or "Estudiante"
        return u.full_name

    return [
        LeaderboardEntryOut(
            rank=idx + 1,
            display_name=_safe_name(user),
            xp_in_classroom=int(xp or 0),
            is_me=(user.id == tenant.user.id),
        )
        for idx, (user, xp) in enumerate(rows)
    ]
