"""Generación de PDFs imprimibles de Guías de Estudio, Temarios y Pruebas Fuertes con ReportLab."""

from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from app.modules.challenges.models import Challenge
from app.modules.courses.models import Lesson, LessonVersion, StudyGuide


def render_study_guide_pdf(*, guide: StudyGuide, course_title: str) -> bytes:
    """Genera un PDF legible e imprimible de una Guía de Estudio, Temario o Metodología."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"VISTAZO LMS • {escape(guide.guide_type.upper())}", styles["Normal"]),
        Spacer(1, 0.2 * cm),
        Paragraph(escape(guide.title), styles["Title"]),
        Paragraph(f"Materia: {escape(course_title)}", styles["Heading3"]),
        Spacer(1, 0.4 * cm),
    ]

    for line in guide.content_markdown.splitlines():
        clean = line.strip()
        if not clean:
            story.append(Spacer(1, 0.2 * cm))
        elif clean.startswith("# "):
            story.append(Paragraph(escape(clean[2:]), styles["Heading2"]))
        elif clean.startswith("## ") or clean.startswith("### "):
            story.append(Paragraph(escape(clean.lstrip("# ")), styles["Heading3"]))
        else:
            story.append(Paragraph(escape(clean), styles["BodyText"]))

    doc.build(story)
    return buf.getvalue()


def render_lesson_exam_pdf(
    *,
    lesson: Lesson,
    lv: LessonVersion,
    challenges: list[Challenge],
    course_title: str,
    include_answers: bool = False,
) -> bytes:
    """Genera un PDF imprimible para aula de una lección o Prueba Fuerte."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"VISTAZO LMS • {'PRUEBA DE CONOCIMIENTO' if lesson.lesson_type == 'strong_exam' else 'GUÍA DE PRÁCTICA'}", styles["Normal"]),
        Spacer(1, 0.2 * cm),
        Paragraph(escape(lesson.title), styles["Title"]),
        Paragraph(
            f"Materia: {escape(course_title)} | Versión v{lv.version_number} | Tiempo sugerido: {lesson.estimated_minutes} min | Nota mínima: {lesson.passing_score_pct}%",
            styles["Normal"],
        ),
        Spacer(1, 0.5 * cm),
    ]

    for idx, ch in enumerate(challenges, start=1):
        story.append(Paragraph(f"<b>{idx}. [{escape(ch.challenge_type)}] ({ch.points} pts)</b> {escape(ch.prompt)}", styles["Heading4"]))
        p = ch.payload_json
        if ch.challenge_type == "visual_concept_card":
            q = p.get("check_question", {})
            story.append(Paragraph(escape(str(q.get("question", ""))), styles["BodyText"]))
            for opt in q.get("options", []):
                story.append(Paragraph(f"[  ] ({escape(str(opt.get('id')))}) {escape(str(opt.get('text')))}", styles["BodyText"]))
        elif ch.challenge_type == "matching":
            lefts = ", ".join(str(x.get("text")) for x in p.get("left_items", []))
            rights = ", ".join(str(x.get("text")) for x in p.get("right_items", []))
            story.append(Paragraph(f"Columna A: {escape(lefts)}", styles["BodyText"]))
            story.append(Paragraph(f"Columna B: {escape(rights)}", styles["BodyText"]))
        elif ch.challenge_type == "sequence_ordering":
            for it in p.get("items", []):
                story.append(Paragraph(f"(  ) {escape(str(it.get('text')))}", styles["BodyText"]))
        elif ch.challenge_type == "fill_in_blanks":
            story.append(Paragraph(escape(str(p.get("template", ""))), styles["BodyText"]))
            if p.get("word_bank"):
                story.append(Paragraph(f"Banco: {escape(', '.join(map(str, p.get('word_bank', []))))}", styles["BodyText"]))
        elif ch.challenge_type == "decision_simulation":
            story.append(Paragraph(escape(str(p.get("scenario_context", ""))), styles["BodyText"]))
        elif ch.challenge_type == "interactive_zones":
            zones = ", ".join(str(z.get("label")) for z in p.get("zones", []))
            story.append(Paragraph(f"Zonas posibles: {escape(zones)}", styles["BodyText"]))
        story.append(Spacer(1, 0.35 * cm))

    if include_answers and challenges:
        story.append(PageBreak())
        story.append(Paragraph("CLAVE DEL EDUCADOR (USO DOCENTE)", styles["Title"]))
        story.append(Spacer(1, 0.3 * cm))
        for idx, ch in enumerate(challenges, start=1):
            story.append(
                Paragraph(
                    f"<b>{idx}. Respuesta esperada:</b> {escape(str(ch.answer_key_json))}<br/>"
                    f"<i>Explicación:</i> {escape(ch.pedagogical_explanation)}",
                    styles["BodyText"],
                )
            )
            story.append(Spacer(1, 0.2 * cm))

    doc.build(story)
    return buf.getvalue()
