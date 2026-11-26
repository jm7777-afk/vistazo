"""Pruebas de integración de Fase 2: SM-2, biblioteca visual, gamificación y analíticas."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import login_and_get_headers


def test_phase2_lesson_unlocks_library_awards_xp_badge_and_analytics(client: TestClient) -> None:
    cadete_headers = login_and_get_headers(client, "cadete@brigada-alfa.org", "BrigadaCadete2026!")
    me = client.get("/api/v1/auth/me", headers=cadete_headers).json()
    org_id = me["memberships"][0]["organization_id"]
    classrooms = client.get(f"/api/v1/orgs/{org_id}/classrooms", headers=cadete_headers).json()
    classroom_id = classrooms[0]["id"]
    courses = client.get(f"/api/v1/orgs/{org_id}/courses", headers=cadete_headers).json()
    detail = client.get(f"/api/v1/courses/{courses[0]['id']}", headers=cadete_headers).json()
    lv_id = detail["modules"][0]["lessons"][0]["active_lesson_version_id"]
    challenges = client.get(f"/api/v1/lesson-versions/{lv_id}/challenges", headers=cadete_headers).json()

    # Provoca un fallo primero en el reto 1 para validar que no descuenta energía en safety-critical
    fail_resp = client.post(
        f"/api/v1/challenges/{challenges[0]['id']}/attempt",
        headers=cadete_headers,
        json={"classroom_id": classroom_id, "submitted_answer": {"selected_option_id": "a"}},
    )
    assert fail_resp.status_code == 200
    assert fail_resp.json()["is_correct"] is False

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
            json={"classroom_id": classroom_id, "submitted_answer": submissions[ch["challenge_type"]]},
        )
        assert last_resp.status_code == 200
        assert last_resp.json()["is_correct"] is True

    assert last_resp is not None
    assert last_resp.json()["unlocked_library_items"] == 2
    assert last_resp.json()["xp_awarded"] > 0

    # Verifica gamificación: XP, racha, energía intacta y medalla FIRST_RESCUE_LESSON
    gam = client.get(f"/api/v1/gamification/me?organization_id={org_id}", headers=cadete_headers).json()
    assert gam["total_xp"] == 115  # 10+15+15+15+20+15 + 25 bonus lección
    assert gam["current_streak_days"] == 1
    assert gam["current_energy"] == 5
    assert any(b["code"] == "FIRST_RESCUE_LESSON" for b in gam["badges"])

    # Verifica biblioteca visual desbloqueada y Entrenamiento Flash
    lib = client.get("/api/v1/library/me", headers=cadete_headers).json()
    assert len(lib) == 2
    asset_id = lib[0]["asset_id"]
    signed_url = lib[0]["signed_url"]

    # El archivo firmado sirve contenido real y bloquea acceso a otro usuario sin membresía
    file_res = client.get(signed_url)
    assert file_res.status_code == 200
    assert "image/svg+xml" in file_res.headers["content-type"]

    flash_res = client.post(
        f"/api/v1/library/flash-review/{asset_id}?toggle_favorite=true",
        headers=cadete_headers,
    )
    assert flash_res.status_code == 200
    assert flash_res.json()["flash_reviews_count"] == 1
    assert flash_res.json()["is_favorite"] is True

    # Usuario libre externo no puede pedir URL firmada de recurso institucional
    client.post(
        "/api/v1/auth/register",
        json={"email": "externo@libre.org", "password": "Password123!", "full_name": "Externo"},
    )
    free_headers = login_and_get_headers(client, "externo@libre.org", "Password123!")
    assert client.get(f"/api/v1/media/{asset_id}/signed-url", headers=free_headers).status_code == 403

    # Sesión de recuperación de energía y repaso espaciado
    sess_resp = client.post(
        "/api/v1/reviews/sessions",
        headers=cadete_headers,
        json={"organization_id": org_id, "session_mode": "energy_recovery", "limit": 3},
    )
    assert sess_resp.status_code == 201
    sess_id = sess_resp.json()["session_id"]
    comp_resp = client.post(
        f"/api/v1/reviews/sessions/{sess_id}/complete",
        headers=cadete_headers,
        json={"items_completed": 3},
    )
    assert comp_resp.status_code == 200

    # Ranking por aula y analíticas para instructor asignado
    lb = client.get(f"/api/v1/orgs/{org_id}/classrooms/{classroom_id}/leaderboard", headers=cadete_headers).json()
    assert len(lb) == 1
    assert lb[0]["is_me"] is True
    assert lb[0]["xp_in_classroom"] == 115

    inst_headers = login_and_get_headers(client, "instructor@brigada-alfa.org", "BrigadaInst2026!")
    analytics = client.get(
        f"/api/v1/orgs/{org_id}/analytics/classrooms/{classroom_id}",
        headers=inst_headers,
    ).json()
    assert analytics["enrolled_students"] == 1
    assert analytics["completed_lesson_records"] == 1
    assert analytics["total_challenge_attempts"] == 7
    assert analytics["overall_accuracy_pct"] > 80.0
