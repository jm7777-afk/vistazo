"""Pruebas de Fase 5: observabilidad, onboarding multi-institucional, analíticas multi-cohorte y GDPR."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import login_and_get_headers


def test_observability_readiness_and_prometheus_metrics(client: TestClient) -> None:
    ready = client.get("/health/ready", headers={"X-Request-ID": "req-test-123"})
    assert ready.status_code == 200
    assert ready.json()["database"] == "ok"
    assert ready.headers["X-Request-ID"] == "req-test-123"
    assert "X-Process-Time-Ms" in ready.headers

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "vistazo_http_requests_total" in metrics.text
    assert "vistazo_http_request_duration_ms_sum" in metrics.text


def test_org_onboarding_multi_cohort_analytics_and_gdpr_anonymize(client: TestClient) -> None:
    admin_headers = login_and_get_headers(client, "superadmin@vistazo.org", "VistazoAdmin2026!")

    onboard = client.post(
        "/api/v1/admin/organizations/onboard",
        headers=admin_headers,
        json={
            "name": "Escuela Primaria Sol",
            "slug": "escuela-sol",
            "sector_type": "primary_school",
            "default_ui_profile": "kids",
            "coordinator_email": "dir@escuela-sol.org",
            "coordinator_name": "Directora Ana Solís",
            "coordinator_password": "SolPassword2026!",
            "initial_program_code": "PRI-CIEN-01",
            "initial_program_title": "Ciencias Naturales Primaria",
            "education_level": "primary",
        },
    )
    assert onboard.status_code == 201, onboard.text
    data = onboard.json()
    new_org_id = data["organization"]["id"]
    assert data["organization"]["default_ui_profile"] == "kids"

    # El nuevo coordinador inicia sesión y consulta analíticas de su propia org
    dir_headers = login_and_get_headers(client, "dir@escuela-sol.org", "SolPassword2026!")
    overview = client.get(f"/api/v1/orgs/{new_org_id}/analytics/overview", headers=dir_headers)
    assert overview.status_code == 200
    assert overview.json()["total_classrooms"] == 0

    # El coordinador de Brigada Alfa NO puede leer analíticas overview de Escuela Sol (403)
    coord_alfa = login_and_get_headers(client, "coord@brigada-alfa.org", "BrigadaCoord2026!")
    assert client.get(f"/api/v1/orgs/{new_org_id}/analytics/overview", headers=coord_alfa).status_code == 403

    # Brigada Alfa sí ve su propio overview con su cohorte piloto
    me_alfa = client.get("/api/v1/auth/me", headers=coord_alfa).json()
    alfa_id = me_alfa["memberships"][0]["organization_id"]
    alfa_overview = client.get(f"/api/v1/orgs/{alfa_id}/analytics/overview", headers=coord_alfa).json()
    assert alfa_overview["total_classrooms"] == 1
    assert len(alfa_overview["cohorts"]) == 1

    # Prueba de anonimización GDPR: registra usuario y anonimiza su cuenta
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "baja@usuario.org",
            "password": "BajaPassword2026!",
            "full_name": "Usuario Temporal",
        },
    )
    baja_headers = login_and_get_headers(client, "baja@usuario.org", "BajaPassword2026!")
    anon = client.post("/api/v1/auth/me/anonymize", headers=baja_headers)
    assert anon.status_code == 204

    # El usuario anonimizado ya no puede autenticarse ni usar el token anterior
    assert client.get("/api/v1/auth/me", headers=baja_headers).status_code == 401
    relogin = client.post(
        "/api/v1/auth/login",
        json={"email": "baja@usuario.org", "password": "BajaPassword2026!"},
    )
    assert relogin.status_code == 401
