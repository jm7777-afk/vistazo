"""Pruebas integrales de Fase 9: Banco de Preguntas, Aleatorización, Open Response, Auto-Certificados, Notas CSV, Familia, Audio/IA, Async Blueprint y Billing SaaS."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.conftest import login_and_get_headers


def _register_educator(client: TestClient, email: str, workspace: str) -> tuple[str, dict[str, str]]:
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": "Dra. Elena Docente",
            "account_type": "educator",
            "workspace_name": workspace,
            "sector_type": "university",
        },
    )
    assert reg.status_code == 201, reg.text
    org_id = reg.json()["memberships"][0]["organization_id"]
    headers = login_and_get_headers(client, email, "Password123!")
    return org_id, headers


def _register_student(client: TestClient, email: str, name: str) -> tuple[str, dict[str, str]]:
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": name,
            "account_type": "student",
        },
    )
    assert reg.status_code == 201, reg.text
    uid = reg.json()["id"]
    headers = login_and_get_headers(client, email, "Password123!")
    return uid, headers


def test_question_bank_randomization_and_open_response_grading(client: TestClient) -> None:
    org_id, edu_headers = _register_educator(client, "bank.edu@vistazo.org", "Facultad Ciencias")

    # 1. Curso, módulo y lección aleatorizada con sample_size=2
    course = client.post(
        f"/api/v1/orgs/{org_id}/courses",
        headers=edu_headers,
        json={
            "title": "Fisiología Avanzada",
            "slug": "fisio-adv-9",
            "education_level": "university",
            "ui_profile": "pro",
            "visibility": "public",
        },
    ).json()
    client.patch(f"/api/v1/orgs/{org_id}/courses/{course['id']}", headers=edu_headers, json={"status": "published"})

    mod = client.post(
        f"/api/v1/orgs/{org_id}/courses/{course['id']}/modules",
        headers=edu_headers,
        json={"title": "Sistema Cardiovascular", "order_index": 1},
    ).json()
    lesson = client.post(
        f"/api/v1/orgs/{org_id}/modules/{mod['id']}/lessons",
        headers=edu_headers,
        json={
            "title": "Examen Aleatorio Cardíaco",
            "slug": "examen-cardiaco-9",
            "order_index": 1,
            "estimated_minutes": 10,
            "lesson_type": "strong_exam",
            "randomize_order": True,
            "sample_size": 2,
        },
    ).json()
    lv = client.post(
        f"/api/v1/orgs/{org_id}/lessons/{lesson['id']}/versions",
        headers=edu_headers,
        json={"summary": "v1"},
    ).json()
    lv_id = lv["id"]

    # 2. Poblar Banco de Preguntas con 3 reactivos + pull-from-bank
    for idx in range(3):
        qb = client.post(
            f"/api/v1/orgs/{org_id}/question-bank",
            headers=edu_headers,
            json={
                "topic_tag": "cardio",
                "challenge_type": "visual_concept_card",
                "schema_version": 1,
                "prompt": f"Pregunta Banco #{idx + 1}: función ventricular",
                "payload_json": {
                    "card_title": f"Concepto #{idx + 1}",
                    "key_points": ["Sístole", "Diástole"],
                    "check_question": {
                        "question": f"Pregunta Banco #{idx + 1}",
                        "options": [{"id": "a", "text": "Correcta"}, {"id": "b", "text": "Falsa"}],
                    },
                },
                "answer_key_json": {"correct_option_id": "a"},
                "pedagogical_explanation": "La sístole impulsa sangre desde los ventrículos.",
                "points": 10,
            },
        )
        assert qb.status_code == 201, qb.text

    listed_qb = client.get(f"/api/v1/orgs/{org_id}/question-bank", headers=edu_headers)
    assert listed_qb.status_code == 200
    assert len(listed_qb.json()) == 3

    pulled = client.post(
        f"/api/v1/orgs/{org_id}/lesson-versions/{lv_id}/pull-from-bank",
        headers=edu_headers,
        json={"count": 3, "topic_tag": "cardio"},
    )
    assert pulled.status_code == 200, pulled.text
    assert len(pulled.json()) == 3

    # 3. Agregar reto open_response
    open_ch = client.post(
        f"/api/v1/orgs/{org_id}/lesson-versions/{lv_id}/challenges",
        headers=edu_headers,
        json={
            "challenge_type": "open_response",
            "schema_version": 1,
            "order_index": 4,
            "prompt": "Explica el gasto cardíaco y su regulación fisiológica.",
            "payload_json": {
                "instruction": "Incluye frecuencia y volumen sistólico.",
                "min_words": 5,
                "keywords_expected": ["frecuencia", "volumen", "ventrículo"],
            },
            "answer_key_json": {
                "reference_answer": "El gasto cardíaco depende de frecuencia cardíaca y volumen sistólico del ventrículo.",
                "rubric_criteria": ["frecuencia", "volumen", "ventrículo"],
                "auto_ai_grade": True,
            },
            "pedagogical_explanation": "GC = FC x VS.",
            "points": 20,
        },
    )
    assert open_ch.status_code == 201, open_ch.text
    open_ch_id = open_ch.json()["id"]

    pub = client.post(f"/api/v1/orgs/{org_id}/lesson-versions/{lv_id}/publish", headers=edu_headers)
    assert pub.status_code == 200

    # Crear programa + pensum + aula para que el estudiante inscrito acceda al curso institucional
    prog = client.post(
        f"/api/v1/orgs/{org_id}/programs",
        headers=edu_headers,
        json={"code": "FIS-9", "title": "Programa Fisiología", "education_level": "university"},
    ).json()
    cv = client.post(
        f"/api/v1/orgs/{org_id}/programs/{prog['id']}/curriculum-versions",
        headers=edu_headers,
        json={"title": "Pensum Fisio v1"},
    ).json()
    client.post(
        f"/api/v1/orgs/{org_id}/curriculum-versions/{cv['id']}/units",
        headers=edu_headers,
        json={"course_id": course["id"], "unit_code": "U1", "title": "Unidad Cardio", "order_index": 1},
    )
    client.post(f"/api/v1/orgs/{org_id}/curriculum-versions/{cv['id']}/publish", headers=edu_headers)
    classroom = client.post(
        f"/api/v1/orgs/{org_id}/classrooms",
        headers=edu_headers,
        json={"curriculum_version_id": cv["id"], "code": "CARDIO-9", "name": "Aula Cardio 9"},
    ).json()

    # 4. Alumno se une al aula, recibe sample_size=2 retos y envía respuesta abierta
    _, stu_headers = _register_student(client, "stu.open@vistazo.org", "Mateo Ruiz")
    joined = client.post(
        "/api/v1/classrooms/join",
        headers=stu_headers,
        json={"invite_code": classroom["invite_code"]},
    )
    assert joined.status_code == 200, joined.text

    player_challenges = client.get(f"/api/v1/lesson-versions/{lv_id}/challenges", headers=stu_headers)
    assert player_challenges.status_code == 200, player_challenges.text
    assert len(player_challenges.json()) == 2  # sample_size=2 aplicado!

    attempt = client.post(
        f"/api/v1/challenges/{open_ch_id}/attempt",
        headers=stu_headers,
        json={
            "client_attempt_id": str(uuid.uuid4()),
            "submitted_answer": {
                "response_text": "El gasto cardiaco resulta de multiplicar frecuencia y volumen del ventriculo izquierdo."
            },
            "response_time_ms": 5000,
        },
    )
    assert attempt.status_code == 200, attempt.text
    assert attempt.json()["score_awarded"] >= 10

    # 5. Educador revisa open_submissions y califica oficialmente
    subs = client.get(f"/api/v1/orgs/{org_id}/open-submissions", headers=edu_headers)
    assert subs.status_code == 200
    assert len(subs.json()) == 1
    sub_id = subs.json()[0]["id"]

    graded = client.patch(
        f"/api/v1/orgs/{org_id}/open-submissions/{sub_id}/grade",
        headers=edu_headers,
        json={"final_score": 19, "teacher_feedback": "Excelente precisión fisiológica."},
    )
    assert graded.status_code == 200
    assert graded.json()["final_score"] == 19
    assert graded.json()["status"] == "graded"


def test_auto_certificates_notes_csv_and_family_portal(client: TestClient) -> None:
    org_id, edu_headers = _register_educator(client, "cert.edu@vistazo.org", "Academia Certificada")

    # Curso + lección mínima + programa + pensum
    course = client.post(
        f"/api/v1/orgs/{org_id}/courses",
        headers=edu_headers,
        json={"title": "Seguridad Vial", "slug": "seg-vial-9", "education_level": "technical", "visibility": "public"},
    ).json()
    client.patch(f"/api/v1/orgs/{org_id}/courses/{course['id']}", headers=edu_headers, json={"status": "published"})
    mod = client.post(
        f"/api/v1/orgs/{org_id}/courses/{course['id']}/modules",
        headers=edu_headers,
        json={"title": "Normas", "order_index": 1},
    ).json()
    lesson = client.post(
        f"/api/v1/orgs/{org_id}/modules/{mod['id']}/lessons",
        headers=edu_headers,
        json={"title": "Cinturón", "slug": "cinturon-9", "order_index": 1, "estimated_minutes": 4},
    ).json()
    lv = client.post(
        f"/api/v1/orgs/{org_id}/lessons/{lesson['id']}/versions",
        headers=edu_headers,
        json={"summary": "v1"},
    ).json()
    ch = client.post(
        f"/api/v1/orgs/{org_id}/lesson-versions/{lv['id']}/challenges",
        headers=edu_headers,
        json={
            "challenge_type": "visual_concept_card",
            "schema_version": 1,
            "order_index": 1,
            "prompt": "Uso correcto del cinturón",
            "payload_json": {
                "card_title": "Seguridad",
                "key_points": ["Ajustado"],
                "check_question": {
                    "question": "¿Dónde pasa?",
                    "options": [{"id": "a", "text": "Hombro y cadera"}, {"id": "b", "text": "Cuello"}],
                },
            },
            "answer_key_json": {"correct_option_id": "a"},
            "pedagogical_explanation": "Evita lesiones cervicales.",
            "points": 100,
        },
    ).json()
    client.post(f"/api/v1/orgs/{org_id}/lesson-versions/{lv['id']}/publish", headers=edu_headers)

    prog = client.post(
        f"/api/v1/orgs/{org_id}/programs",
        headers=edu_headers,
        json={"code": "VIAL-1", "title": "Certificación Vial", "education_level": "technical"},
    ).json()
    cv = client.post(
        f"/api/v1/orgs/{org_id}/programs/{prog['id']}/curriculum-versions",
        headers=edu_headers,
        json={"title": "Pensum Vial v1"},
    ).json()
    client.post(
        f"/api/v1/orgs/{org_id}/curriculum-versions/{cv['id']}/units",
        headers=edu_headers,
        json={"course_id": course["id"], "unit_code": "U1", "title": "Unidad Única", "order_index": 1},
    )
    pub_cv = client.post(f"/api/v1/orgs/{org_id}/curriculum-versions/{cv['id']}/publish", headers=edu_headers)
    assert pub_cv.status_code == 200
    classroom = client.post(
        f"/api/v1/orgs/{org_id}/classrooms",
        headers=edu_headers,
        json={"curriculum_version_id": cv["id"], "code": "VIAL-A9", "name": "Aula Vial A9"},
    ).json()

    # Estudiante se une al aula, completa la lección y reclama certificado automático
    _, stu_headers = _register_student(client, "stu.cert9@vistazo.org", "Lucia Fernandez")
    joined = client.post(
        "/api/v1/classrooms/join",
        headers=stu_headers,
        json={"invite_code": classroom["invite_code"]},
    )
    assert joined.status_code == 200, joined.text

    attempt = client.post(
        f"/api/v1/challenges/{ch['id']}/attempt",
        headers=stu_headers,
        json={
            "client_attempt_id": str(uuid.uuid4()),
            "classroom_id": classroom["id"],
            "submitted_answer": {"selected_option_id": "a"},
            "response_time_ms": 900,
        },
    )
    assert attempt.status_code == 200, attempt.text

    claimed = client.post("/api/v1/certificates/claim-eligible", headers=stu_headers)
    assert claimed.status_code == 200, claimed.text
    assert len(claimed.json()) == 1
    assert claimed.json()[0]["curriculum_version_id"] == cv["id"]

    # Apuntes personales + Exportación e Importación CSV Anki
    note = client.post(
        "/api/v1/notes/me",
        headers=stu_headers,
        json={"title": "Regla 3 segundos", "content": "Distancia mínima en autopista.", "is_flashcard": True},
    )
    assert note.status_code == 201, note.text

    csv_export = client.get("/api/v1/notes/me/flashcards-csv", headers=stu_headers)
    assert csv_export.status_code == 200
    assert "Regla 3 segundos" in csv_export.text

    csv_import = client.post(
        "/api/v1/notes/me/import-csv",
        headers=stu_headers,
        json={"csv_text": 'Front,Back\n"Señal STOP","Detención obligatoria total"'},
    )
    assert csv_import.status_code == 201
    assert any(n["title"] == "Señal STOP" for n in csv_import.json())

    # Portal Familiar (código + resumen anonimizado)
    fam_code_resp = client.get("/api/v1/auth/me/family-code", headers=stu_headers)
    assert fam_code_resp.status_code == 200
    fam_code = fam_code_resp.json()["family_access_code"]
    assert fam_code.startswith("FAM-")

    guardian = client.get(f"/api/v1/auth/guardian/summary?code={fam_code}")
    assert guardian.status_code == 200, guardian.text
    assert guardian.json()["completed_lessons_count"] >= 1
    assert guardian.json()["student_initials"]


def test_media_ai_illustration_audio_async_blueprint_and_billing(client: TestClient) -> None:
    org_id, edu_headers = _register_educator(client, "saas.edu@vistazo.org", "Instituto SaaS 9")

    # 1. Ilustración IA (usa fallback SVG determinista si provider=svg_fallback o red no disponible)
    illus = client.post(
        f"/api/v1/orgs/{org_id}/media/ai-illustration",
        headers=edu_headers,
        json={"topic": "Estructura de la Neurona", "style": "scientific", "visibility": "public"},
    )
    assert illus.status_code == 201, illus.text
    assert illus.json()["signed_url"]

    # 2. Subida de audio_clip
    audio_up = client.post(
        f"/api/v1/orgs/{org_id}/media",
        headers=edu_headers,
        data={"title": "Pronunciación Fonética", "tags": "audio,lenguas", "visibility": "public"},
        files={"file": ("clip.mp3", b"ID3dummy-audio-bytes", "audio/mpeg")},
    )
    assert audio_up.status_code == 201, audio_up.text
    assert audio_up.json()["media_format"] == "audio_clip"

    # 3. Blueprint asíncrono + consulta /tasks/{task_id}
    queued = client.post(
        f"/api/v1/orgs/{org_id}/ai/generate-blueprint-async",
        headers=edu_headers,
        json={
            "topic": "Astronomía Moderna",
            "education_level": "university",
            "source_text": "Estudia la evolución estelar, exoplanetas y cosmología observacional.",
            "save_to_course": True,
        },
    )
    assert queued.status_code == 202, queued.text
    task_id = queued.json()["task_id"]

    task_status = client.get(f"/api/v1/tasks/{task_id}", headers=edu_headers)
    assert task_status.status_code == 200
    assert task_status.json()["status"] in {"queued", "running", "completed"}

    # 4. SaaS Billing: planes, suscripción org, checkout sandbox y webhook Stripe
    plans = client.get("/api/v1/billing/plans")
    assert plans.status_code == 200
    assert any(p["plan_code"] == "educator_pro" for p in plans.json())

    current_sub = client.get(f"/api/v1/orgs/{org_id}/billing", headers=edu_headers)
    assert current_sub.status_code == 200
    assert current_sub.json()["plan_code"] == "free"

    checkout = client.post(
        f"/api/v1/orgs/{org_id}/billing/checkout",
        headers=edu_headers,
        json={"plan_code": "educator_pro"},
    )
    assert checkout.status_code == 200
    assert checkout.json()["subscription"]["plan_code"] == "educator_pro"
    assert checkout.json()["subscription"]["max_students"] == 250

    # Simular webhook Stripe con metadata (con firma si STRIPE_WEBHOOK_SECRET configurado)
    payload_bytes = json.dumps(
        {
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {"organization_id": org_id, "plan_code": "institution"}}},
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    secret = get_settings().stripe_webhook_secret
    if secret:
        ts = "1700000000"
        sig = hmac.new(secret.encode("utf-8"), f"{ts}.".encode("utf-8") + payload_bytes, hashlib.sha256).hexdigest()
        headers["Stripe-Signature"] = f"t={ts},v1={sig}"

    wh = client.post("/api/v1/billing/webhooks/stripe", content=payload_bytes, headers=headers)
    assert wh.status_code == 200
    after_wh = client.get(f"/api/v1/orgs/{org_id}/billing", headers=edu_headers)
    assert after_wh.json()["plan_code"] == "institution"
    assert after_wh.json()["max_students"] == 5000
