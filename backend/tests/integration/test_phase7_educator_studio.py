"""Pruebas integrales de Fase 7: Registro Educador vs Estudiante, Estudio CRUD, IA Avanzada e Imágenes Dinámicas."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.modules.media.dynamic_visuals import sanitize_svg_markup
from tests.conftest import login_and_get_headers


def test_register_educator_vs_student_and_full_studio_flow(client: TestClient) -> None:
    # 1. Registro como estudiante estándar
    stu_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "nuevo.estudiante@vistazo.org",
            "password": "Password123!",
            "full_name": "Mateo Estudiante",
            "account_type": "student",
            "preferred_ui_profile": "youth",
        },
    )
    assert stu_reg.status_code == 201, stu_reg.text
    assert stu_reg.json()["account_type"] == "student"
    assert stu_reg.json()["memberships"] == []

    # 2. Registro como educador: provisiona espacio docente propio con permisos completos
    edu_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "profe.ana@vistazo.org",
            "password": "Password123!",
            "full_name": "Ana Profesora",
            "account_type": "educator",
            "workspace_name": "Academia de Física Ana",
            "sector_type": "university",
            "preferred_ui_profile": "pro",
        },
    )
    assert edu_reg.status_code == 201, edu_reg.text
    edu_user = edu_reg.json()
    assert edu_user["account_type"] == "educator"
    assert len(edu_user["memberships"]) == 1
    org_id = edu_user["memberships"][0]["organization_id"]
    assert edu_user["memberships"][0]["organization_name"] == "Academia de Física Ana"

    edu_headers = login_and_get_headers(client, "profe.ana@vistazo.org", "Password123!")
    stu_headers = login_and_get_headers(client, "nuevo.estudiante@vistazo.org", "Password123!")

    # Estudiante NO puede entrar al espacio del educador (403)
    assert client.get(f"/api/v1/orgs/{org_id}/courses", headers=stu_headers).status_code == 403

    # 3. Arquitecto IA: genera Blueprint (Curso + Módulos + Nodos + Guía Metodológica) guardado en borrador
    bp_resp = client.post(
        f"/api/v1/orgs/{org_id}/ai/generate-blueprint",
        headers=edu_headers,
        json={
            "topic": "Leyes de Newton y Dinámica",
            "education_level": "university",
            "ui_profile": "pro",
            "pedagogy_style": "problem_based",
            "modules_count": 2,
            "source_text": "Primera ley de inercia. Segunda ley fuerza igual masa por aceleración. Tercera ley acción y reacción.",
            "save_to_course": True,
        },
    )
    assert bp_resp.status_code == 201, bp_resp.text
    bp = bp_resp.json()
    course_id = bp["created_course_id"]
    guide_id = bp["created_guide_id"]
    assert course_id is not None
    assert guide_id is not None
    assert len(bp["blueprint"]["modules"]) == 2

    # 4. CRUD sobre cursos, módulos, lecciones y guías
    upd_course = client.patch(
        f"/api/v1/orgs/{org_id}/courses/{course_id}",
        headers=edu_headers,
        json={"title": "Mecánica Clásica y Dinámica", "status": "published"},
    )
    assert upd_course.status_code == 200
    assert upd_course.json()["title"] == "Mecánica Clásica y Dinámica"
    assert upd_course.json()["status"] == "published"

    detail = client.get(f"/api/v1/courses/{course_id}", headers=edu_headers).json()
    lesson_id = detail["modules"][0]["lessons"][0]["id"]
    lv_id = detail["modules"][0]["lessons"][0]["active_lesson_version_id"]

    # 5. Generar Prueba Fuerte IA sobre la versión borrador
    strong_resp = client.post(
        f"/api/v1/orgs/{org_id}/ai/generate-strong-exam",
        headers=edu_headers,
        json={
            "lesson_version_id": lv_id,
            "source_text": (
                "Todo cuerpo persevera en su estado de reposo o movimiento uniforme si la fuerza neta es cero. "
                "La aceleración es directamente proporcional a la fuerza neta e inversamente proporcional a la masa. "
                "Toda acción genera una reacción de igual magnitud y sentido contrario sobre cuerpos distintos."
            ),
            "difficulty_target": 4,
            "question_count": 5,
        },
    )
    assert strong_resp.status_code == 201, strong_resp.text
    assert strong_resp.json()["challenges_created"] == 5

    # Verificar CRUD manual de reto (editar + eliminar)
    ch_list = client.get(f"/api/v1/orgs/{org_id}/lesson-versions/{lv_id}/challenges", headers=edu_headers).json()
    assert len(ch_list) == 5
    first_ch_id = ch_list[0]["id"]
    patched_ch = client.patch(
        f"/api/v1/orgs/{org_id}/challenges/{first_ch_id}",
        headers=edu_headers,
        json={"points": 35, "prompt": "Reto editado manualmente por la docente"},
    )
    assert patched_ch.status_code == 200
    assert patched_ch.json()["points"] == 35

    # 6. Generar Imagen Dinámica SVG con IA y enlazar como reto interactive_zones
    vis_resp = client.post(
        f"/api/v1/orgs/{org_id}/ai/generate-dynamic-visual",
        headers=edu_headers,
        json={
            "topic": "Ciclo de Análisis de Fuerzas",
            "diagram_kind": "cycle",
            "context_text": "Identificar el sistema. Dibujar diagrama de cuerpo libre. Sumar fuerzas. Resolver aceleración.",
            "education_level": "university",
            "lesson_version_id": lv_id,
            "create_interactive_challenge": True,
        },
    )
    assert vis_resp.status_code == 201, vis_resp.text
    vis = vis_resp.json()
    assert vis["created_challenge_id"] is not None
    assert len(vis["zones"]) >= 2

    # La imagen dinámica SVG se sirve correctamente por URL firmada
    svg_resp = client.get(vis["signed_url"])
    assert svg_resp.status_code == 200
    assert "image/svg+xml" in svg_resp.headers["content-type"]
    assert "<svg" in svg_resp.text

    # Publicar guía de estudio y versión de lección
    pub_guide = client.patch(
        f"/api/v1/orgs/{org_id}/study-guides/{guide_id}",
        headers=edu_headers,
        json={"status": "published"},
    )
    assert pub_guide.status_code == 200
    assert pub_guide.json()["status"] == "published"

    pub_lv = client.post(f"/api/v1/orgs/{org_id}/lesson-versions/{lv_id}/publish", headers=edu_headers)
    assert pub_lv.status_code == 200
    assert pub_lv.json()["status"] == "published"

    # Eliminar guía creada y comprobar que ya no se lista
    assert client.delete(f"/api/v1/orgs/{org_id}/study-guides/{guide_id}", headers=edu_headers).status_code == 204
    guides_after = client.get(f"/api/v1/orgs/{org_id}/study-guides", headers=edu_headers).json()
    assert all(g["id"] != guide_id for g in guides_after)


def test_superadmin_global_content_crud_and_svg_sanitization(client: TestClient) -> None:
    # Verifica sanitización SVG contra XSS
    dirty = '<svg viewBox="0 0 100 100" onload="alert(1)"><script>evil()</script><rect width="10" height="10"/></svg>'
    clean = sanitize_svg_markup(dirty)
    assert "<script" not in clean.lower()
    assert "onload" not in clean.lower()
    assert "<rect" in clean

    admin_headers = login_and_get_headers(client, "superadmin@vistazo.org", "VistazoAdmin2026!")
    inst_headers = login_and_get_headers(client, "instructor@brigada-alfa.org", "BrigadaInst2026!")

    # Instructor normal NO puede usar endpoints globales de SuperAdmin
    assert client.get("/api/v1/admin/courses", headers=inst_headers).status_code == 403

    # SuperAdmin crea curso global + módulo + nodo + guía + reto manual + publicación
    g_course = client.post(
        "/api/v1/admin/courses",
        headers=admin_headers,
        json={
            "title": "Pensamiento Crítico Global",
            "slug": "pensamiento-critico-global",
            "description": "Curso público creado por SuperAdmin",
            "education_level": "specialized",
            "ui_profile": "pro",
            "visibility": "public",
        },
    )
    assert g_course.status_code == 201, g_course.text
    cid = g_course.json()["id"]
    assert g_course.json()["visibility"] == "public"

    g_mod = client.post(
        f"/api/v1/admin/courses/{cid}/modules",
        headers=admin_headers,
        json={"title": "Módulo 1 Global", "order_index": 1},
    ).json()
    g_les = client.post(
        f"/api/v1/admin/modules/{g_mod['id']}/lessons",
        headers=admin_headers,
        json={
            "title": "Evaluación Fuerte Global",
            "slug": "eval-fuerte-global",
            "order_index": 1,
            "estimated_minutes": 10,
            "lesson_type": "strong_exam",
            "passing_score_pct": 85,
        },
    ).json()
    lv_id = g_les["active_lesson_version_id"]

    g_guide = client.post(
        "/api/v1/admin/ai/generate-study-guide",
        headers=admin_headers,
        json={
            "course_id": cid,
            "guide_type": "guia_estudio",
            "topic": "Argumentación lógica",
            "source_text": "Premisa mayor, premisa menor y conclusión válida sin falacias formales.",
            "save_as_draft": True,
        },
    ).json()
    assert g_guide["saved_guide_id"] is not None

    client.patch(
        f"/api/v1/admin/study-guides/{g_guide['saved_guide_id']}",
        headers=admin_headers,
        json={"status": "published"},
    )

    ch_created = client.post(
        f"/api/v1/admin/lesson-versions/{lv_id}/challenges",
        headers=admin_headers,
        json={
            "challenge_type": "visual_concept_card",
            "order_index": 1,
            "prompt": "Identifica la estructura válida de un argumento.",
            "payload_json": {
                "card_title": "Silogismo válido",
                "key_points": ["Premisas verdaderas", "Inferencia válida"],
                "check_question": {
                    "question": "¿Qué garantiza la validez lógica?",
                    "options": [
                        {"id": "a", "text": "La conclusión se deduce necesariamente de las premisas"},
                        {"id": "b", "text": "Repetir la conclusión más fuerte"},
                    ],
                },
            },
            "answer_key_json": {"correct_option_id": "a"},
            "pedagogical_explanation": "La validez depende de la forma lógica entre premisas y conclusión.",
            "difficulty": 4,
            "points": 20,
        },
    )
    assert ch_created.status_code == 201, ch_created.text
    assert client.post(f"/api/v1/admin/lesson-versions/{lv_id}/publish", headers=admin_headers).status_code == 200

    # Visible en catálogo público y sus guías publicadas visibles para cualquier usuario
    catalog = client.get("/api/v1/catalog/courses").json()
    assert any(c["id"] == cid for c in catalog)
    pub_guides = client.get(f"/api/v1/courses/{cid}/study-guides").json()
    assert len(pub_guides) == 1
