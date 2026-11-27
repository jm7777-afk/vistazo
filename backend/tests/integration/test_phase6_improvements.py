"""Pruebas de mejoras de producción, preferencias de onboarding, revisión de borradores y PDF resiliente."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.modules.certificates.service import get_certificates_storage_root
from tests.conftest import login_and_get_headers


def test_user_onboarding_preferences_and_persist(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "nuevo@usuario.org",
            "password": "PasswordSegura123!",
            "full_name": "Nuevo Aprendiz",
        },
    )
    headers = login_and_get_headers(client, "nuevo@usuario.org", "PasswordSegura123!")
    me_before = client.get("/api/v1/auth/me", headers=headers).json()
    assert me_before["onboarding_completed"] is False
    assert me_before["daily_goal_minutes"] == 5

    upd = client.patch(
        "/api/v1/auth/me/preferences",
        headers=headers,
        json={
            "preferred_ui_profile": "youth",
            "daily_goal_minutes": 15,
            "onboarding_completed": True,
        },
    )
    assert upd.status_code == 200
    body = upd.json()
    assert body["preferred_ui_profile"] == "youth"
    assert body["daily_goal_minutes"] == 15
    assert body["onboarding_completed"] is True


def test_instructor_can_list_draft_versions_and_challenges(client: TestClient) -> None:
    inst_headers = login_and_get_headers(client, "instructor@brigada-alfa.org", "BrigadaInst2026!")
    me = client.get("/api/v1/auth/me", headers=inst_headers).json()
    org_id = me["memberships"][0]["organization_id"]
    courses = client.get(f"/api/v1/orgs/{org_id}/courses", headers=inst_headers).json()
    detail = client.get(f"/api/v1/courses/{courses[0]['id']}", headers=inst_headers).json()
    lesson_id = detail["modules"][0]["lessons"][0]["id"]

    versions = client.get(f"/api/v1/orgs/{org_id}/lessons/{lesson_id}/versions", headers=inst_headers)
    assert versions.status_code == 200
    assert len(versions.json()) >= 1
    lv_id = versions.json()[0]["id"]

    ch_list = client.get(f"/api/v1/orgs/{org_id}/lesson-versions/{lv_id}/challenges", headers=inst_headers)
    assert ch_list.status_code == 200
    assert len(ch_list.json()) == 6
    assert "answer_key_json" in ch_list.json()[0]


def test_certificate_pdf_regenerates_if_ephemeral_file_missing(client: TestClient) -> None:
    coord_headers = login_and_get_headers(client, "coord@brigada-alfa.org", "BrigadaCoord2026!")
    me_coord = client.get("/api/v1/auth/me", headers=coord_headers).json()
    org_id = me_coord["memberships"][0]["organization_id"]
    programs = client.get(f"/api/v1/orgs/{org_id}/programs", headers=coord_headers).json()
    cvs = client.get(
        f"/api/v1/orgs/{org_id}/programs/{programs[0]['id']}/curriculum-versions",
        headers=coord_headers,
    ).json()

    cadete_headers = login_and_get_headers(client, "cadete@brigada-alfa.org", "BrigadaCadete2026!")
    classrooms = client.get(f"/api/v1/orgs/{org_id}/classrooms", headers=cadete_headers).json()
    classroom_id = classrooms[0]["id"]
    courses = client.get(f"/api/v1/orgs/{org_id}/courses", headers=cadete_headers).json()
    detail = client.get(f"/api/v1/courses/{courses[0]['id']}", headers=cadete_headers).json()
    lv_id = detail["modules"][0]["lessons"][0]["active_lesson_version_id"]
    challenges = client.get(f"/api/v1/lesson-versions/{lv_id}/challenges", headers=cadete_headers).json()

    submissions = {
        "visual_concept_card": {"selected_option_id": "b"},
        "matching": {"pairs": {"l1": "r2", "l2": "r1", "l3": "r3"}},
        "sequence_ordering": {"ordered_ids": ["s3", "s1", "s2"]},
        "interactive_zones": {"tap_point": {"x": 0.39, "y": 0.48}},
        "decision_simulation": {"chosen_sequence": ["c2", "c3"]},
        "fill_in_blanks": {"answers": {"b1": "30", "b2": "2", "b3": "5 a 6"}},
    }
    for ch in challenges:
        client.post(
            f"/api/v1/challenges/{ch['id']}/attempt",
            headers=cadete_headers,
            json={"classroom_id": classroom_id, "submitted_answer": submissions[ch["challenge_type"]]},
        )

    cert = client.post(
        f"/api/v1/orgs/{org_id}/certificates/issue",
        headers=coord_headers,
        json={"student_email": "cadete@brigada-alfa.org", "curriculum_version_id": cvs[0]["id"]},
    ).json()

    # Simula pérdida del archivo PDF en disco efímero de Render
    pdf_path = get_certificates_storage_root() / "orgs" / org_id / f"{cert['id']}.pdf"
    if pdf_path.exists():
        pdf_path.unlink()

    dl = client.get(f"/api/v1/certificates/{cert['id']}/pdf", headers=cadete_headers)
    assert dl.status_code == 200
    assert dl.content.startswith(b"%PDF")


def test_production_rejects_default_insecure_jwt_secret(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "dev-only-insecure-secret-change-in-production-32chars")
    try:
        try:
            create_app()
            assert False, "Debió fallar con JWT_SECRET_KEY insegura en producción"
        except RuntimeError:
            pass
    finally:
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        get_settings.cache_clear()
