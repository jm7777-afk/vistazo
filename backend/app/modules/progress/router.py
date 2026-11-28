"""Endpoints de evaluación server-side y consulta de progreso."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.challenges.evaluators import get_challenge_handler
from app.modules.challenges.models import Challenge, OpenSubmission
from app.modules.courses.models import Course, Lesson, LessonVersion, Module
from app.modules.curriculum.models import Classroom, ClassroomMember
from app.modules.gamification.service import apply_challenge_gamification
from app.modules.media.service import unlock_lesson_media_for_student
from app.modules.progress.models import ChallengeAttempt, LessonProgress, StudentCompetency
from app.modules.progress.schemas import (
    LessonProgressOut,
    StudentCompetencyOut,
    StudentProgressOverview,
    SubmitAttemptRequest,
    SubmitAttemptResponse,
)
from app.modules.spaced_repetition.service import record_challenge_review
from app.modules.tenants.models import OrganizationMember

router = APIRouter(tags=["progress"])


@router.post("/challenges/{challenge_id}/attempt", response_model=SubmitAttemptResponse)
def submit_challenge_attempt(
    challenge_id: uuid.UUID,
    payload: SubmitAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubmitAttemptResponse:
    """Evalúa un reto exclusivamente en backend, registra el intento y actualiza progreso."""
    row = db.execute(
        select(Challenge, LessonVersion, Course)
        .join(LessonVersion, Challenge.lesson_version_id == LessonVersion.id)
        .join(Lesson, LessonVersion.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .where(
            Challenge.id == challenge_id,
            Challenge.deleted_at.is_(None),
            Challenge.status == "published",
            Course.deleted_at.is_(None),
        )
    ).first()
    if not row:
        raise NotFoundError("Reto no encontrado o no publicado")

    ch, lv, course = row
    org_id: uuid.UUID | None = course.organization_id
    classroom_obj: Classroom | None = None

    if payload.classroom_id is not None:
        classroom_obj = db.scalar(
            select(Classroom).where(Classroom.id == payload.classroom_id, Classroom.deleted_at.is_(None))
        )
        if not classroom_obj:
            raise NotFoundError("Aula no encontrada")
        if org_id is not None and classroom_obj.organization_id != org_id:
            raise ForbiddenError("El aula no corresponde a la organización del curso")
        org_id = classroom_obj.organization_id
        if not current_user.is_super_admin:
            enrolled = db.scalar(
                select(ClassroomMember).where(
                    ClassroomMember.classroom_id == classroom_obj.id,
                    ClassroomMember.user_id == current_user.id,
                    ClassroomMember.deleted_at.is_(None),
                    ClassroomMember.enrollment_status == "enrolled",
                )
            )
            if not enrolled:
                raise ForbiddenError("Debes estar matriculado en el aula para registrar progreso institucional")
    elif course.visibility != "public" and not current_user.is_super_admin:
        member = db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == course.organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.deleted_at.is_(None),
                OrganizationMember.status == "active",
            )
        )
        if not member:
            raise ForbiddenError("No tienes acceso a este curso institucional")

    # Idempotencia para reintentos de red / PWA offline
    if payload.client_attempt_id is not None:
        existing_attempt = db.scalar(
            select(ChallengeAttempt).where(
                ChallengeAttempt.client_attempt_id == payload.client_attempt_id,
                ChallengeAttempt.user_id == current_user.id,
            )
        )
        if existing_attempt:
            lp = db.scalar(
                select(LessonProgress).where(
                    LessonProgress.user_id == current_user.id,
                    LessonProgress.lesson_version_id == lv.id,
                    LessonProgress.classroom_id == payload.classroom_id
                    if payload.classroom_id is not None
                    else LessonProgress.classroom_id.is_(None),
                )
            )
            return SubmitAttemptResponse(
                attempt_id=existing_attempt.id,
                challenge_id=ch.id,
                is_correct=existing_attempt.is_correct,
                score_awarded=existing_attempt.score_awarded,
                max_points=ch.points,
                pedagogical_explanation=ch.pedagogical_explanation,
                detail={"idempotent_replay": True},
                lesson_status=lp.status if lp else "in_progress",
                lesson_score_pct=lp.best_score_pct if lp else Decimal("0.00"),
                completed_challenges=lp.completed_challenges if lp else 0,
                total_challenges=lp.total_challenges if lp else 0,
            )

    prev_attempts_count = db.scalar(
        select(func.count(ChallengeAttempt.id)).where(
            ChallengeAttempt.user_id == current_user.id,
            ChallengeAttempt.challenge_id == ch.id,
        )
    )

    handler = get_challenge_handler(ch.challenge_type, ch.schema_version)
    eval_result = handler.evaluate(
        payload_raw=ch.payload_json,
        answer_key_raw=ch.answer_key_json,
        submission_raw=payload.submitted_answer,
        max_points=ch.points,
        is_safety_critical=ch.is_safety_critical,
    )

    attempt = ChallengeAttempt(
        client_attempt_id=payload.client_attempt_id,
        user_id=current_user.id,
        organization_id=org_id,
        classroom_id=payload.classroom_id,
        challenge_id=ch.id,
        submitted_answer_json=payload.submitted_answer,
        is_correct=eval_result.is_correct,
        score_awarded=eval_result.score_awarded,
        response_time_ms=payload.response_time_ms,
        hints_used=payload.hints_used,
        attempt_number=int(prev_attempts_count or 0) + 1,
    )
    db.add(attempt)
    if ch.challenge_type == "open_response":
        db.add(
            OpenSubmission(
                organization_id=org_id,
                challenge_id=ch.id,
                user_id=current_user.id,
                response_text=str(payload.submitted_answer.get("response_text", "")),
                attachment_note=payload.submitted_answer.get("attachment_note"),
                max_points=ch.points,
                ai_suggested_score=eval_result.score_awarded,
                ai_feedback=str(eval_result.detail.get("rubric_feedback", "")),
                status="pending_review",
            )
        )
    db.flush()

    # Recalcular progreso en esta lesson_version_id
    all_challenges = db.scalars(
        select(Challenge).where(
            Challenge.lesson_version_id == lv.id,
            Challenge.deleted_at.is_(None),
            Challenge.status == "published",
        )
    ).all()
    total_challenges = len(all_challenges)
    max_total_points = sum(item.points for item in all_challenges) or 1

    best_by_challenge: dict[uuid.UUID, tuple[bool, int]] = {}
    attempts_for_lv = db.scalars(
        select(ChallengeAttempt).where(
            ChallengeAttempt.user_id == current_user.id,
            ChallengeAttempt.challenge_id.in_([c.id for c in all_challenges]),
            ChallengeAttempt.classroom_id == payload.classroom_id
            if payload.classroom_id is not None
            else ChallengeAttempt.classroom_id.is_(None),
        )
    ).all()
    for att in attempts_for_lv:
        prev_correct, prev_score = best_by_challenge.get(att.challenge_id, (False, 0))
        best_by_challenge[att.challenge_id] = (
            prev_correct or att.is_correct,
            max(prev_score, att.score_awarded),
        )

    completed_challenges = sum(1 for is_ok, _ in best_by_challenge.values() if is_ok)
    earned_points = sum(score for _, score in best_by_challenge.values())
    score_pct = Decimal(str(round((earned_points / max_total_points) * 100, 2)))
    is_lesson_completed = total_challenges > 0 and completed_challenges == total_challenges

    lp = db.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_version_id == lv.id,
            LessonProgress.classroom_id == payload.classroom_id
            if payload.classroom_id is not None
            else LessonProgress.classroom_id.is_(None),
        )
    )
    now = datetime.now(timezone.utc)
    was_completed_before = lp is not None and lp.status == "completed"
    if not lp:
        lp = LessonProgress(
            user_id=current_user.id,
            organization_id=org_id,
            classroom_id=payload.classroom_id,
            lesson_version_id=lv.id,
            status="completed" if is_lesson_completed else "in_progress",
            best_score_pct=score_pct,
            completed_challenges=completed_challenges,
            total_challenges=total_challenges,
            completed_at=now if is_lesson_completed else None,
            last_activity_at=now,
        )
        db.add(lp)
    else:
        lp.best_score_pct = max(lp.best_score_pct, score_pct)
        lp.completed_challenges = completed_challenges
        lp.total_challenges = total_challenges
        lp.last_activity_at = now
        if is_lesson_completed:
            lp.status = "completed"
            lp.completed_at = lp.completed_at or now

    lesson_just_completed = is_lesson_completed and not was_completed_before

    # Actualiza competencia asociada si existe
    if ch.competency_id is not None:
        comp_scope_filter = (
            StudentCompetency.organization_id == org_id
            if org_id is not None
            else StudentCompetency.organization_id.is_(None)
        )
        sc = db.scalar(
            select(StudentCompetency).where(
                StudentCompetency.user_id == current_user.id,
                StudentCompetency.competency_id == ch.competency_id,
                comp_scope_filter,
            )
        )
        attempt_pct = Decimal("100.00") if eval_result.is_correct else Decimal("0.00")
        if not sc:
            sc = StudentCompetency(
                user_id=current_user.id,
                organization_id=org_id,
                competency_id=ch.competency_id,
                mastery_score=attempt_pct,
                evaluated_attempts=1,
                mastery_status="achieved" if attempt_pct >= Decimal("80.00") else "in_progress",
                last_evaluated_at=now,
            )
            db.add(sc)
        else:
            prev_n = sc.evaluated_attempts
            new_score = ((sc.mastery_score * prev_n) + attempt_pct) / (prev_n + 1)
            sc.mastery_score = new_score.quantize(Decimal("0.01"))
            sc.evaluated_attempts = prev_n + 1
            sc.mastery_status = "achieved" if sc.mastery_score >= Decimal("80.00") else "in_progress"
            sc.last_evaluated_at = now

    # Repetición espaciada SM-2, gamificación y desbloqueo de biblioteca visual
    sr_item = record_challenge_review(
        db,
        user_id=current_user.id,
        organization_id=org_id,
        challenge=ch,
        is_correct=eval_result.is_correct,
        attempt_number=attempt.attempt_number,
        hints_used=attempt.hints_used,
        response_time_ms=attempt.response_time_ms,
        now=now,
    )
    apply_challenge_gamification(
        db,
        user_id=current_user.id,
        organization_id=org_id,
        classroom_id=payload.classroom_id,
        challenge_id=ch.id,
        is_correct=eval_result.is_correct,
        score_awarded=eval_result.score_awarded,
        is_safety_critical=ch.is_safety_critical,
        energy_enabled=classroom_obj.energy_enabled if classroom_obj else False,
        max_energy=classroom_obj.max_energy if classroom_obj else 5,
        lesson_just_completed=lesson_just_completed,
    )
    unlocked_count = 0
    if lesson_just_completed:
        unlocked_count = unlock_lesson_media_for_student(
            db,
            user_id=current_user.id,
            lesson_version_id=lv.id,
            challenge_ids=[item.id for item in all_challenges],
        )

    xp_awarded = eval_result.score_awarded + (25 if lesson_just_completed else 0)
    db.commit()
    return SubmitAttemptResponse(
        attempt_id=attempt.id,
        challenge_id=ch.id,
        is_correct=eval_result.is_correct,
        score_awarded=eval_result.score_awarded,
        max_points=ch.points,
        pedagogical_explanation=ch.pedagogical_explanation,
        detail=eval_result.detail,
        lesson_status=lp.status,
        lesson_score_pct=lp.best_score_pct,
        completed_challenges=lp.completed_challenges,
        total_challenges=lp.total_challenges,
        xp_awarded=xp_awarded,
        next_review_at=sr_item.next_review_at,
        unlocked_library_items=unlocked_count,
    )


@router.get("/progress/me", response_model=StudentProgressOverview)
def my_progress(
    organization_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudentProgressOverview:
    lp_stmt = select(LessonProgress).where(LessonProgress.user_id == current_user.id)
    sc_stmt = select(StudentCompetency).where(StudentCompetency.user_id == current_user.id)
    if organization_id is not None:
        lp_stmt = lp_stmt.where(LessonProgress.organization_id == organization_id)
        sc_stmt = sc_stmt.where(StudentCompetency.organization_id == organization_id)

    lessons = db.scalars(lp_stmt.order_by(LessonProgress.last_activity_at.desc())).all()
    comps = db.scalars(sc_stmt.order_by(StudentCompetency.last_evaluated_at.desc())).all()
    return StudentProgressOverview(
        lessons=[
            LessonProgressOut(
                id=l.id,
                lesson_version_id=l.lesson_version_id,
                classroom_id=l.classroom_id,
                organization_id=l.organization_id,
                status=l.status,
                best_score_pct=l.best_score_pct,
                completed_challenges=l.completed_challenges,
                total_challenges=l.total_challenges,
                completed_at=l.completed_at,
                last_activity_at=l.last_activity_at,
            )
            for l in lessons
        ],
        competencies=[
            StudentCompetencyOut(
                competency_id=c.competency_id,
                organization_id=c.organization_id,
                mastery_score=c.mastery_score,
                evaluated_attempts=c.evaluated_attempts,
                mastery_status=c.mastery_status,
                last_evaluated_at=c.last_evaluated_at,
            )
            for c in comps
        ],
    )
