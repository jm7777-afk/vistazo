"""Pruebas integrales de Fase 8: Invite QR, PDF/DOCX extractor, Export PDF, Reset Password, Live Quiz, Remediation & Notifications."""

from __future__ import annotations

import io
from docx import Document
from fastapi.testclient import TestClient

from app.modules.auth.models import EmailVerificationToken, ParentalConsent, PasswordResetToken, User
from app.modules.auth.service import generate_opaque_token, hash_token
from app.modules.media.storage import load_media_bytes, save_media_bytes
from tests.conftest import login_and_get_headers


def test_document_extraction_qr_invites_pdf_export_and_live_quiz(client: TestClient, session_factory) -> None:
    edu_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "profe.phase8@vistazo.org",
            "password": "Password123!",
            "full_name": "Carlos Docente",
            "account_type": "educator",
            "workspace_name": "Instituto Fase 8",
            "sector_type": "high_school",
        },
    )
    assert edu_reg.status_code == 201
    org_id = edu_reg.json()["memberships"][0]["organization_id"]
    edu_headers = login_and_get_headers(client, "profe.phase8@vistazo.org", "Password123!")

    # 1. Extraer texto desde DOCX real con python-docx
    docx_buf = io.BytesIO()
    doc = Document()
    doc.add_paragraph("La fotosíntesis convierte energía solar en glucosa y oxígeno.")
    doc.add_paragraph("Ocurre en los cloroplastos mediante fase luminosa y ciclo de Calvin.")
    doc.save(docx_buf)
    docx_buf.seek(0)

    ext_resp = client.post(
        f"/api/v1/orgs/{org_id}/ai/extract-document",
        headers=edu_headers,
        files={"file": ("guia.docx", docx_buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert ext_resp.status_code == 200, ext_resp.text
    assert "fotosíntesis" in ext_resp.json()["extracted_text"]

    # 2. Crear blueprint con guía + curso + lección
    bp = client.post(
        f"/api/v1/orgs/{org_id}/ai/generate-blueprint",
        headers=edu_headers,
        json={
            "topic": "Fotosíntesis y Metabolismo",
            "education_level": "high_school",
            "source_text": ext_resp.json()["extracted_text"],
            "save_to_course": True,
        },
    ).json()
    course_id = bp["created_course_id"]
    guide_id = bp["created_guide_id"]
    client.patch(f"/api/v1/orgs/{org_id}/courses/{course_id}", headers=edu_headers, json={"status": "published"})
    client.patch(f"/api/v1/orgs/{org_id}/study-guides/{guide_id}", headers=edu_headers, json={"status": "published"})

    detail = client.get(f"/api/v1/courses/{course_id}", headers=edu_headers).json()
    lv_id = detail["modules"][0]["lessons"][0]["active_lesson_version_id"]

    # Generar Prueba Fuerte + exportar PDF guía y PDF examen con clave
    client.post(
        f"/api/v1/orgs/{org_id}/ai/generate-strong-exam",
        headers=edu_headers,
        json={"lesson_version_id": lv_id, "source_text": ext_resp.json()["extracted_text"], "question_count": 5},
    )
    guide_pdf = client.get(f"/api/v1/orgs/{org_id}/study-guides/{guide_id}/pdf", headers=edu_headers)
    assert guide_pdf.status_code == 200
    assert guide_pdf.content.startswith(b"%PDF")

    exam_pdf = client.get(f"/api/v1/orgs/{org_id}/lesson-versions/{lv_id}/exam-pdf?include_answers=true", headers=edu_headers)
    assert exam_pdf.status_code == 200
    assert exam_pdf.content.startswith(b"%PDF")

    # 3. Crear programa + pensum publicado + aula con código de invitación y QR SVG
    prog = client.post(
        f"/api/v1/orgs/{org_id}/programs",
        headers=edu_headers,
        json={"code": "BIO-HS", "title": "Biología Bachillerato", "education_level": "high_school"},
    ).json()
    cv = client.post(
        f"/api/v1/orgs/{org_id}/programs/{prog['id']}/curriculum-versions",
        headers=edu_headers,
        json={"title": "Pensum Biología v1"},
    ).json()
    client.post(
        f"/api/v1/orgs/{org_id}/curriculum-versions/{cv['id']}/units",
        headers=edu_headers,
        json={"course_id": course_id, "unit_code": "U1", "title": "Unidad 1", "order_index": 1},
    )
    client.post(f"/api/v1/orgs/{org_id}/curriculum-versions/{cv['id']}/publish", headers=edu_headers)

    classroom = client.post(
        f"/api/v1/orgs/{org_id}/classrooms",
        headers=edu_headers,
        json={"curriculum_version_id": cv["id"], "code": "BIO-2026", "name": "Aula Biología A"},
    ).json()
    invite_code = classroom["invite_code"]
    assert invite_code and invite_code.startswith("VZT-")

    qr_resp = client.get(f"/api/v1/orgs/{org_id}/classrooms/{classroom['id']}/invite-qr", headers=edu_headers)
    assert qr_resp.status_code == 200
    assert "<svg" in qr_resp.text

    # Estudiante previsualiza y se une con el código
    stu_reg = client.post(
        "/api/v1/auth/register",
        json={"email": "alumna.p8@vistazo.org", "password": "Password123!", "full_name": "Sofía Alumna", "account_type": "student"},
    )
    assert stu_reg.status_code == 201
    stu_headers = login_and_get_headers(client, "alumna.p8@vistazo.org", "Password123!")

    preview = client.get(f"/api/v1/classrooms/invite/{invite_code}")
    assert preview.status_code == 200
    assert preview.json()["classroom_name"] == "Aula Biología A"

    joined = client.post("/api/v1/classrooms/join", headers=stu_headers, json={"invite_code": invite_code})
    assert joined.status_code == 200
    assert joined.json()["status"] == "joined"

    # 4. Clase en Vivo (Live Quiz)
    client.post(f"/api/v1/orgs/{org_id}/lesson-versions/{lv_id}/publish", headers=edu_headers)
    live = client.post(
        f"/api/v1/orgs/{org_id}/live-sessions",
        headers=edu_headers,
        json={"lesson_version_id": lv_id, "title": "Repaso en Vivo Fotosíntesis"},
    )
    assert live.status_code == 201, live.text
    room_code = live.json()["room_code"]

    p_join = client.post(f"/api/v1/live-sessions/{room_code}/join", json={"display_name": "Sofía Vivo"}).json()
    adv = client.post(f"/api/v1/live-sessions/{room_code}/advance", headers=edu_headers)
    assert adv.status_code == 200
    assert adv.json()["status"] == "active"
    assert "answer_key_json" not in str(adv.json()["current_challenge"])

    ans_resp = client.post(
        f"/api/v1/live-sessions/{room_code}/answer",
        json={"participant_id": p_join["participant_id"], "submitted_answer": {"chosen_sequence": ["c1", "c3"]}},
    )
    assert ans_resp.status_code == 200

    # 5. Refuerzo adaptativo IA + notificaciones + storage helper
    rem = client.post(
        "/api/v1/ai/adaptive-remediation",
        headers=stu_headers,
        json={"course_id": course_id, "missed_prompts": ["Ciclo de Calvin"]},
    )
    assert rem.status_code == 200
    assert "Refuerzo" in rem.json()["title"]

    notifs = client.get("/api/v1/notifications/me", headers=stu_headers)
    assert notifs.status_code == 200
    assert "reminders" in notifs.json()

    sub = client.post(
        "/api/v1/notifications/subscribe",
        headers=stu_headers,
        json={"endpoint": "https://push.example/sub/123", "device_label": "Chrome Test"},
    )
    assert sub.status_code == 201

    backend_used = save_media_bytes("tests/sample.txt", b"hola vistazo", "text/plain")
    assert backend_used == "local"
    assert load_media_bytes("tests/sample.txt") == b"hola vistazo"


def test_password_reset_and_token_verifications(client: TestClient, session_factory) -> None:
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "menor.p8@vistazo.org",
            "password": "OldPassword123!",
            "full_name": "Lucas Menor",
            "account_type": "student",
            "birth_date": "2016-05-10",
            "guardian_name": "Elena Tutora",
            "guardian_email": "tutora@vistazo.org",
        },
    )
    assert reg.status_code == 201

    # Forgot password no revela existencia
    fp = client.post("/api/v1/auth/forgot-password", json={"email": "noexiste@vistazo.org"})
    assert fp.status_code == 200

    # Simula tokens emitidos para reset, email y consentimiento parental
    reset_raw = generate_opaque_token()
    email_raw = generate_opaque_token()
    parent_raw = generate_opaque_token()
    from datetime import datetime, timedelta, timezone

    with session_factory() as db:
        u = db.query(User).filter(User.email == "menor.p8@vistazo.org").one()
        db.add(
            PasswordResetToken(
                user_id=u.id,
                token_hash=hash_token(reset_raw),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
            )
        )
        db.add(
            EmailVerificationToken(
                user_id=u.id,
                token_hash=hash_token(email_raw),
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        consent = db.query(ParentalConsent).filter(ParentalConsent.minor_user_id == u.id).one()
        consent.verification_token_hash = hash_token(parent_raw)
        db.commit()

    assert client.post("/api/v1/auth/verify-email", json={"token": email_raw}).status_code == 200
    assert client.post("/api/v1/auth/verify-parental-consent", json={"token": parent_raw}).status_code == 200
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            json={"token": reset_raw, "new_password": "NewStrongPassword123!"},
        ).status_code
        == 200
    )

    # Nueva contraseña funciona y correo aparece verificado
    new_headers = login_and_get_headers(client, "menor.p8@vistazo.org", "NewStrongPassword123!")
    me = client.get("/api/v1/auth/me", headers=new_headers).json()
    assert me["email_verified"] is True
