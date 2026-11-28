"""Endpoints de apuntes personales, subrayados y flashcards CSV/Anki."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.challenges.models import Challenge
from app.modules.notes.models import StudentNote
from app.modules.spaced_repetition.models import SpacedRepetitionItem

router = APIRouter(prefix="/notes", tags=["notes"])


class NoteCreate(BaseModel):
    course_id: uuid.UUID | None = None
    lesson_id: uuid.UUID | None = None
    study_guide_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=8000)
    highlight_quote: str | None = Field(default=None, max_length=2000)
    is_flashcard: bool = False


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=8000)
    is_flashcard: bool | None = None


class NoteOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID | None
    lesson_id: uuid.UUID | None
    study_guide_id: uuid.UUID | None
    title: str
    content: str
    highlight_quote: str | None
    is_flashcard: bool
    updated_at: datetime


class ImportCsvRequest(BaseModel):
    csv_text: str = Field(min_length=3, max_length=30000)
    course_id: uuid.UUID | None = None


def _to_out(n: StudentNote) -> NoteOut:
    return NoteOut(
        id=n.id,
        course_id=n.course_id,
        lesson_id=n.lesson_id,
        study_guide_id=n.study_guide_id,
        title=n.title,
        content=n.content,
        highlight_quote=n.highlight_quote,
        is_flashcard=n.is_flashcard,
        updated_at=n.updated_at,
    )


@router.get("/me", response_model=list[NoteOut])
def list_my_notes(
    course_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NoteOut]:
    stmt = select(StudentNote).where(StudentNote.user_id == current_user.id)
    if course_id is not None:
        stmt = stmt.where(StudentNote.course_id == course_id)
    rows = db.scalars(stmt.order_by(StudentNote.updated_at.desc())).all()
    return [_to_out(r) for r in rows]


@router.post("/me", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_my_note(
    payload: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteOut:
    note = StudentNote(
        user_id=current_user.id,
        course_id=payload.course_id,
        lesson_id=payload.lesson_id,
        study_guide_id=payload.study_guide_id,
        title=payload.title.strip(),
        content=payload.content.strip(),
        highlight_quote=payload.highlight_quote.strip() if payload.highlight_quote else None,
        is_flashcard=payload.is_flashcard,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _to_out(note)


@router.patch("/me/{note_id}", response_model=NoteOut)
def update_my_note(
    note_id: uuid.UUID,
    payload: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoteOut:
    note = db.scalar(select(StudentNote).where(StudentNote.id == note_id, StudentNote.user_id == current_user.id))
    if not note:
        raise NotFoundError("Apunte no encontrado")
    if payload.title is not None:
        note.title = payload.title.strip()
    if payload.content is not None:
        note.content = payload.content.strip()
    if payload.is_flashcard is not None:
        note.is_flashcard = payload.is_flashcard
    db.commit()
    db.refresh(note)
    return _to_out(note)


@router.delete("/me/{note_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_my_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    note = db.scalar(select(StudentNote).where(StudentNote.id == note_id, StudentNote.user_id == current_user.id))
    if not note:
        raise NotFoundError("Apunte no encontrado")
    db.delete(note)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me/flashcards-csv")
def export_flashcards_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Exporta apuntes flashcard e ítems SM-2 en formato CSV compatible con Anki."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Front", "Back", "Tag"])

    notes = db.scalars(select(StudentNote).where(StudentNote.user_id == current_user.id)).all()
    for n in notes:
        writer.writerow([n.title, n.content, "vistazo-note"])

    sr_rows = db.execute(
        select(SpacedRepetitionItem, Challenge)
        .join(Challenge, SpacedRepetitionItem.challenge_id == Challenge.id)
        .where(SpacedRepetitionItem.user_id == current_user.id, Challenge.deleted_at.is_(None))
        .limit(50)
    ).all()
    for _sr, ch in sr_rows:
        writer.writerow([ch.prompt, ch.pedagogical_explanation, f"sm2-{ch.challenge_type}"])

    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="vistazo-flashcards.csv"'},
    )


@router.post("/me/import-csv", response_model=list[NoteOut], status_code=status.HTTP_201_CREATED)
def import_flashcards_csv(
    payload: ImportCsvRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NoteOut]:
    reader = csv.reader(io.StringIO(payload.csv_text.strip()))
    created: list[StudentNote] = []
    for idx, row in enumerate(reader):
        if not row or len(row) < 2:
            continue
        front, back = row[0].strip(), row[1].strip()
        if idx == 0 and front.lower() in {"front", "frente", "pregunta", "titulo"}:
            continue
        if not front or not back:
            continue
        note = StudentNote(
            user_id=current_user.id,
            course_id=payload.course_id,
            title=front[:200],
            content=back[:8000],
            is_flashcard=True,
        )
        db.add(note)
        created.append(note)
        if len(created) >= 50:
            break
    db.commit()
    for n in created:
        db.refresh(n)
    return [_to_out(n) for n in created]
