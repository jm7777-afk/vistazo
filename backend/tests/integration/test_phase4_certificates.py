"""Pruebas de integración de Fase 4: emisión, PDF/QR, verificación pública y revocación."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.modules.certificates.service import reset_verify_rate_limiter
from tests.conftest import login_and_get_headers


def test_certificate_issue_pdf_public_verify_and_revoke(client: TestClient) -> None:
    reset_verify_rate_limiter()
    coord_headers = login_and_get_headers(client, "coord@brigada-alfa.org", "BrigadaCoord2026!")
    me_coord = client.get("/api/v1/auth/me", headers=coord_headers).json()
    org_id = me_coord["memberships"][0]["organization_id"]
    programs = client.get(f"/api/v1/orgs/{org_id}/programs", headers=coord_headers).json()
    cvs = client.get(
        f"/api/v1/orgs/{org_id}/programs/{programs[0]['id']}/curriculum-versions",
        headers=coord_headers,
    ).json()
    cv_id = cvs[0]["id"]

    # Antes de completar el pensum -> emisión rechazada (422)
    early = client.post(
        f"/api/v1/orgs/{org_id}/certificates/issue",
        headers=coord_headers,
        json={"student_email": "cadete@brigada-alfa.org", "curriculum_version_id": cv_id},
    )
    assert early.status_code == 422

    # Cadete completa la lección del pensum
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
        r = client.post(
            f"/api/v1/challenges/{ch['id']}/attempt",
            headers=cadete_headers,
            json={"classroom_id": classroom_id, "submitted_answer": submissions[ch["challenge_type"]]},
        )
        assert r.status_code == 200

    # Coordinador emite certificado -> BackgroundTask genera PDF y marca issued
    issued_resp = client.post(
        f"/api/v1/orgs/{org_id}/certificates/issue",
        headers=coord_headers,
        json={
            "student_email": "cadete@brigada-alfa.org",
            "curriculum_version_id": cv_id,
            "classroom_id": classroom_id,
            "signer_title": "Comandante de Brigada",
        },
    )
    assert issued_resp.status_code == 201, issued_resp.text
    cert = issued_resp.json()
    v_hash = cert["verification_hash"]

    # Cadete puede listar y descargar su PDF real
    my_certs = client.get("/api/v1/certificates/me", headers=cadete_headers).json()
    assert len(my_certs) == 1
    assert my_certs[0]["status"] == "issued"
    assert my_certs[0]["has_pdf"] is True

    pdf_resp = client.get(f"/api/v1/certificates/{cert['id']}/pdf", headers=cadete_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")

    # Ruta pública GET /verificar-certificado/{hash} sin login ni PII sensible
    pub_resp = client.get(f"/verificar-certificado/{v_hash}")
    assert pub_resp.status_code == 200, pub_resp.text
    pub = pub_resp.json()
    assert pub["valid"] is True
    assert pub["status"] == "issued"
    assert pub["recipient_initials"] == "C. L. M."
    assert "cadete@brigada-alfa.org" not in str(pub)

    # Hash malformado o inexistente devuelve 404 uniforme
    assert client.get("/verificar-certificado/not-a-valid-hash").status_code == 404
    assert client.get(f"/verificar-certificado/{'0' * 64}").status_code == 404

    # Revocación y verificación posterior
    rev_resp = client.post(
        f"/api/v1/orgs/{org_id}/certificates/{cert['id']}/revoke",
        headers=coord_headers,
        json={"reason": "Actualización obligatoria de protocolo vencida"},
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["status"] == "revoked"

    pub_after = client.get(f"/verificar-certificado/{v_hash}").json()
    assert pub_after["valid"] is False
    assert pub_after["status"] == "revoked"
    assert "Actualización obligatoria" in pub_after["revocation_reason"]
