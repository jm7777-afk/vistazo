"""Pruebas de integración de flujos MVP: estudio libre, piloto rescate y versionado."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from tests.conftest import login_and_get_headers


def test_minor_registration_requires_guardian_info(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "menor@escuela.org",
            "password": "MenorPassword123!",
            "full_name": "Estudiante Menor",
            "birth_date": "2016-05-10",
            "preferred_ui_profile": "kids",
        },
    )
    assert resp.status_code == 422

    ok_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "menor@escuela.org",
            "password": "MenorPassword123!",
            "full_name": "Estudiante Menor",
            "birth_date": "2016-05-10",
            "preferred_ui_profile": "kids",
            "guardian_name": "Ana Pérez",
            "guardian_email": "ana.perez@familia.org",
        },
    )
    assert ok_resp.status_code == 201
    assert ok_resp.json()["is_minor"] is True


def test_free_study_catalog_and_attempt_flow(client: TestClient) -> None:
    # Catálogo público accesible sin login
    catalog = client.get("/api/v1/catalog/courses")
    assert catalog.status_code == 200
    courses = catalog.json()
    assert len(courses) >= 1
    public_course_id = courses[0]["id"]

    detail = client.get(f"/api/v1/courses/{public_course_id}").json()
    lv_id = detail["modules"][0]["lessons"][0]["active_lesson_version_id"]
    challenges = client.get(f"/api/v1/lesson-versions/{lv_id}/challenges").json()
    assert len(challenges) == 1

    # Usuario libre se registra y resuelve el reto
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "visitante@libre.org",
            "password": "LibrePassword123!",
            "full_name": "Visitante Libre",
        },
    )
    headers = login_and_get_headers(client, "visitante@libre.org", "LibrePassword123!")
    attempt_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/challenges/{challenges[0]['id']}/attempt",
        headers=headers,
        json={
            "client_attempt_id": attempt_id,
            "submitted_answer": {"ordered_ids": ["p1", "p2", "p3"]},
            "response_time_ms": 4200,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_correct"] is True
    assert body["lesson_status"] == "completed"
    assert float(body["lesson_score_pct"]) == 100.0

    # Reintento idempotente devuelve el mismo resultado sin duplicar
    replay = client.post(
        f"/api/v1/challenges/{challenges[0]['id']}/attempt",
        headers=headers,
        json={
            "client_attempt_id": attempt_id,
            "submitted_answer": {"ordered_ids": ["p1", "p2", "p3"]},
        },
    )
    assert replay.status_code == 200
    assert replay.json()["attempt_id"] == body["attempt_id"]


def test_rescue_brigade_full_lesson_and_version_preservation(client: TestClient) -> None:
    cadete_headers = login_and_get_headers(client, "cadete@brigada-alfa.org", "BrigadaCadete2026!")
    me = client.get("/api/v1/auth/me", headers=cadete_headers).json()
    org_id = me["memberships"][0]["organization_id"]

    classrooms = client.get(f"/api/v1/orgs/{org_id}/classrooms", headers=cadete_headers).json()
    classroom_id = classrooms[0]["id"]
    courses = client.get(f"/api/v1/orgs/{org_id}/courses", headers=cadete_headers).json()
    detail = client.get(f"/api/v1/courses/{courses[0]['id']}", headers=cadete_headers).json()
    lesson = detail["modules"][0]["lessons"][0]
    lv1_id = lesson["active_lesson_version_id"]

    challenges = client.get(f"/api/v1/lesson-versions/{lv1_id}/challenges", headers=cadete_headers).json()
    assert len(challenges) == 6

    submissions = {
        "visual_concept_card": {"selected_option_id": "b"},
        "matching": {"pairs": {"l1": "r2", "l2": "r1", "l3": "r3"}},
        "sequence_ordering": {"ordered_ids": ["s3", "s1", "s2"]},
        "interactive_zones": {"tap_point": {"x": 0.39, "y": 0.48}},
        "decision_simulation": {"chosen_sequence": ["c2", "c3"]},
        "fill_in_blanks": {"answers": {"b1": "30", "b2": "2", "b3": "5 a 6"}},
    }

    last_resp = None
    for ch in challenges:
        last_resp = client.post(
            f"/api/v1/challenges/{ch['id']}/attempt",
            headers=cadete_headers,
            json={
                "classroom_id": classroom_id,
                "submitted_answer": submissions[ch["challenge_type"]],
                "response_time_ms": 5000,
            },
        )
        assert last_resp.status_code == 200, last_resp.text
        assert last_resp.json()["is_correct"] is True

    assert last_resp is not None
    assert last_resp.json()["lesson_status"] == "completed"
    assert float(last_resp.json()["lesson_score_pct"]) == 100.0

    # Instructor publica v2 de la misma lección -> el progreso de v1 debe conservarse intacto
    inst_headers = login_and_get_headers(client, "instructor@brigada-alfa.org", "BrigadaInst2026!")
    v2_resp = client.post(
        f"/api/v1/orgs/{org_id}/lessons/{lesson['id']}/versions",
        headers=inst_headers,
        json={"summary": "Actualización protocolo 2026", "requires_revalidation": False},
    )
    assert v2_resp.status_code == 201
    v2_id = v2_resp.json()["id"]

    ch_v2 = client.post(
        f"/api/v1/orgs/{org_id}/lesson-versions/{v2_id}/challenges",
        headers=inst_headers,
        json={
            "challenge_type": "visual_concept_card",
            "order_index": 1,
            "prompt": "Nuevo protocolo v2",
            "payload_json": {
                "card_title": "Protocolo v2",
                "key_points": ["Verificar EPP completo"],
                "check_question": {
                    "question": "¿Qué verificar primero?",
                    "options": [{"id": "a", "text": "EPP"}, {"id": "b", "text": "Nada"}],
                },
            },
            "answer_key_json": {"correct_option_id": "a"},
            "pedagogical_explanation": "Siempre EPP primero.",
            "is_safety_critical": True,
        },
    )
    assert ch_v2.status_code == 201
    pub_v2 = client.post(f"/api/v1/orgs/{org_id}/lesson-versions/{v2_id}/publish", headers=inst_headers)
    assert pub_v2.status_code == 200

    # El cadete conserva su progreso completado en v1
    prog = client.get(f"/api/v1/progress/me?organization_id={org_id}", headers=cadete_headers).json()
    v1_prog = next(p for p in prog["lessons"] if p["lesson_version_id"] == lv1_id)
    assert v1_prog["status"] == "completed"
    assert float(v1_prog["best_score_pct"]) == 100.0
    assert len(prog["competencies"]) == 1
    assert prog["competencies"][0]["mastery_status"] == "achieved"
