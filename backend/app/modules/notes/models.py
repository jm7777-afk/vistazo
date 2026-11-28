"""Modelos de apuntes personales, subrayados y flashcards del estudiante."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StudentNote(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Apunte personal o flashcard creada por el estudiante/educador."""

    __tablename__ = "student_notes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True
    )
    study_guide_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("study_guides.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    highlight_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_flashcard: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
