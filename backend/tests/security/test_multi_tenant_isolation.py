"""Pruebas de seguridad: aislamiento multi-tenant, RBAC, IDOR y tokens."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import login_and_get_headers


def test_cross_tenant_isolation_between_organizations(client: TestClient) -> None:
    admin_headers = login_and_get_headers(client, "superadmin@vistazo.org", "VistazoAdmin2026!")

    # Crea Organización B independiente
    org_b_resp = client.post(
        "/api/v1/admin/organizations",
        headers=admin_headers,
        json={
            "name": "Colegio Horizonte",
            "slug": "colegio-horizonte",
            "sector_type": "secondary_school",
            "default_ui_profile": "youth",
        },
    )
    assert org_b_resp.status_code == 201, org_b_resp.text
    org_b_id = org_b_resp.json()["id"]

    # Registra coordinador para Org B
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "coord.b@horizonte.org",
            "password": "PasswordSegura123!",
            "full_name": "Coordinador B",
            "preferred_ui_profile": "youth",
        },
    )
    assert reg_resp.status_code == 201
    client.post(
        f"/api/v1/orgs/{org_b_id}/members",
        headers=admin_headers,
        json={"user_email": "coord.b@horizonte.org", "role_code": "coordinator"},
    )

    # Identifica Org A (Brigada de Rescate Alfa) desde el coordinador A
    coord_a_headers = login_and_get_headers(client, "coord@brigada-alfa.org", "BrigadaCoord2026!")
    me_a = client.get("/api/v1/auth/me", headers=coord_a_headers).json()
    org_a_id = me_a["memberships"][0]["organization_id"]

    # Coordinador B intenta leer miembros, aulas, programas y auditoría de Org A -> 403
    coord_b_headers = login_and_get_headers(client, "coord.b@horizonte.org", "PasswordSegura123!")
    assert client.get(f"/api/v1/orgs/{org_a_id}/members", headers=coord_b_headers).status_code == 403
    assert client.get(f"/api/v1/orgs/{org_a_id}/classrooms", headers=coord_b_headers).status_code == 403
    assert client.get(f"/api/v1/orgs/{org_a_id}/programs", headers=coord_b_headers).status_code == 403
    assert client.get(f"/api/v1/orgs/{org_a_id}/audit-logs", headers=coord_b_headers).status_code == 403
    assert (
        client.post(
            f"/api/v1/orgs/{org_a_id}/programs",
            headers=coord_b_headers,
            json={"code": "HACK-1", "title": "Intruso", "education_level": "rescue"},
        ).status_code
        == 403
    )


def test_instructor_cannot_access_unassigned_classroom(client: TestClient) -> None:
    coord_headers = login_and_get_headers(client, "coord@brigada-alfa.org", "BrigadaCoord2026!")
    me = client.get("/api/v1/auth/me", headers=coord_headers).json()
    org_id = me["memberships"][0]["organization_id"]

    # Obtiene pensum publicado y crea un segundo aula SIN asignar al instructor
    programs = client.get(f"/api/v1/orgs/{org_id}/programs", headers=coord_headers).json()
    cvs = client.get(f"/api/v1/orgs/{org_id}/programs/{programs[0]['id']}/curriculum-versions", headers=coord_headers).json()
    c2_resp = client.post(
        f"/api/v1/orgs/{org_id}/classrooms",
        headers=coord_headers,
        json={
            "curriculum_version_id": cvs[0]["id"],
            "code": "COHORTE-PRIVADA-B",
            "name": "Cohorte B No Asignada",
        },
    )
    assert c2_resp.status_code == 201
    classroom_b_id = c2_resp.json()["id"]

    inst_headers = login_and_get_headers(client, "instructor@brigada-alfa.org", "BrigadaInst2026!")
    visible_classrooms = client.get(f"/api/v1/orgs/{org_id}/classrooms", headers=inst_headers).json()
    assert all(c["id"] != classroom_b_id for c in visible_classrooms)

    # Intento directo por IDOR debe retornar 403
    assert (
        client.get(f"/api/v1/orgs/{org_id}/classrooms/{classroom_b_id}/students", headers=inst_headers).status_code
        == 403
    )


def test_answer_key_never_exposed_and_private_course_blocked(client: TestClient) -> None:
    # Usuario libre sin membresía institucional
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "libre@ciudadano.org",
            "password": "CiudadanoPass2026!",
            "full_name": "Usuario Libre",
        },
    )
    free_headers = login_and_get_headers(client, "libre@ciudadano.org", "CiudadanoPass2026!")

    # Obtiene el curso institucional vía cadete autorizado para conocer su lesson_version_id
    cadete_headers = login_and_get_headers(client, "cadete@brigada-alfa.org", "BrigadaCadete2026!")
    me_cadete = client.get("/api/v1/auth/me", headers=cadete_headers).json()
    org_id = me_cadete["memberships"][0]["organization_id"]
    org_courses = client.get(f"/api/v1/orgs/{org_id}/courses", headers=cadete_headers).json()
    course_detail = client.get(f"/api/v1/courses/{org_courses[0]['id']}", headers=cadete_headers).json()
    lv_id = course_detail["modules"][0]["lessons"][0]["active_lesson_version_id"]

    # Usuario libre no puede acceder al curso ni a los retos de Brigada Alfa
    assert client.get(f"/api/v1/courses/{org_courses[0]['id']}", headers=free_headers).status_code == 403
    assert client.get(f"/api/v1/lesson-versions/{lv_id}/challenges", headers=free_headers).status_code == 403

    # Cadete sí puede ver los retos, pero nunca recibe answer_key_json
    challenges = client.get(f"/api/v1/lesson-versions/{lv_id}/challenges", headers=cadete_headers).json()
    assert len(challenges) == 6
    for ch in challenges:
        assert "answer_key_json" not in ch
        assert "answer_key" not in ch
        assert "pedagogical_explanation" not in ch


def test_refresh_token_rotation_and_reuse_detection(client: TestClient) -> None:
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "cadete@brigada-alfa.org", "password": "BrigadaCadete2026!"},
    )
    assert login_resp.status_code == 200
    csrf1 = login_resp.json()["csrf_token"]
    refresh1 = client.cookies.get("vistazo_refresh")
    assert refresh1 is not None

    # Primera rotación válida
    r1 = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf1})
    assert r1.status_code == 200
    csrf2 = r1.json()["csrf_token"]
    refresh2 = client.cookies.get("vistazo_refresh")
    assert refresh2 != refresh1

    # Reuso malicioso del refresh1 antiguo -> detecta compromiso y revoca la familia
    client.cookies.set("vistazo_refresh", refresh1)
    client.cookies.set("vistazo_csrf", csrf1)
    reuse = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf1})
    assert reuse.status_code == 401

    # El token válido refresh2 también queda revocado por compromiso de familia
    client.cookies.set("vistazo_refresh", refresh2)
    client.cookies.set("vistazo_csrf", csrf2)
    after = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf2})
    assert after.status_code == 401
