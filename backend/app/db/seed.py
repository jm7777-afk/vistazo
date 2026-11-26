"""Script idempotente de carga inicial (Piloto Brigada de Rescate + Estudio Libre)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.modules.auth.models import User
from app.modules.challenges.models import Challenge
from app.modules.courses.models import Course, Lesson, LessonVersion, Module
from app.modules.curriculum.models import (
    Classroom,
    ClassroomMember,
    Competency,
    CurriculumUnit,
    CurriculumVersion,
    InstructorAssignment,
    Program,
)
from app.modules.gamification.models import Badge
from app.modules.media.models import ChallengeMediaAsset, MediaAsset
from app.modules.rbac.models import Permission, Role, RolePermission
from app.modules.tenants.models import Organization, OrganizationMember

SYSTEM_PERMISSIONS = [
    ("org:manage", "organization", "manage", "Administrar miembros y configuración de organización"),
    ("curriculum:manage", "curriculum", "manage", "Crear y publicar programas, competencias y pensums"),
    ("classroom:manage", "classroom", "manage", "Crear aulas, asignar instructores y matricular estudiantes"),
    ("classroom:view_assigned", "classroom", "read", "Ver aulas asignadas y progreso de estudiantes"),
    ("lesson:author", "lesson", "write", "Crear y publicar lecciones y retos"),
    ("certificate:issue", "certificate", "issue", "Emitir y revocar certificados"),
    ("ai:generate", "ai", "execute", "Generar borradores con asistente pedagógico IA"),
]

SYSTEM_ROLES = {
    "coordinator": (
        "Coordinador Institucional",
        [
            "org:manage",
            "curriculum:manage",
            "classroom:manage",
            "classroom:view_assigned",
            "lesson:author",
            "certificate:issue",
            "ai:generate",
        ],
    ),
    "instructor": (
        "Instructor",
        ["classroom:view_assigned", "lesson:author", "ai:generate"],
    ),
    "student": ("Estudiante", []),
}


def seed_database(db: Session) -> None:
    """Crea permisos, roles, organización piloto Brigada de Rescate Alfa y los 6 tipos de retos."""
    existing_perm = db.scalar(select(Permission).where(Permission.code == "org:manage"))
    if existing_perm:
        return

    perm_map: dict[str, Permission] = {}
    for code, resource, action, desc in SYSTEM_PERMISSIONS:
        perm = Permission(code=code, resource=resource, action=action, description=desc)
        db.add(perm)
        perm_map[code] = perm
    db.flush()

    role_map: dict[str, Role] = {}
    for role_code, (role_name, perm_codes) in SYSTEM_ROLES.items():
        role = Role(organization_id=None, code=role_code, name=role_name, is_system=True)
        db.add(role)
        db.flush()
        role_map[role_code] = role
        for p_code in perm_codes:
            db.add(RolePermission(role_id=role.id, permission_id=perm_map[p_code].id))

    # Usuarios demo con credenciales conocidas para desarrollo/piloto
    superadmin = User(
        email="superadmin@vistazo.org",
        password_hash=hash_password("VistazoAdmin2026!"),
        full_name="Super Administrador Vistazo",
        is_super_admin=True,
        preferred_ui_profile="pro",
    )
    coordinator = User(
        email="coord@brigada-alfa.org",
        password_hash=hash_password("BrigadaCoord2026!"),
        full_name="Comandante Elena Rojas",
        preferred_ui_profile="pro",
    )
    instructor = User(
        email="instructor@brigada-alfa.org",
        password_hash=hash_password("BrigadaInst2026!"),
        full_name="Instructor Marcos Vega",
        preferred_ui_profile="pro",
    )
    student = User(
        email="cadete@brigada-alfa.org",
        password_hash=hash_password("BrigadaCadete2026!"),
        full_name="Cadete Lucía Méndez",
        preferred_ui_profile="pro",
    )
    db.add_all([superadmin, coordinator, instructor, student])
    db.flush()

    brigada = Organization(
        name="Brigada de Rescate Alfa",
        slug="brigada-alfa",
        sector_type="rescue_brigade",
        default_ui_profile="pro",
        settings_json={"pilot": True, "energy_default": False},
    )
    db.add(brigada)
    db.flush()

    db.add_all(
        [
            OrganizationMember(organization_id=brigada.id, user_id=coordinator.id, role_id=role_map["coordinator"].id),
            OrganizationMember(organization_id=brigada.id, user_id=instructor.id, role_id=role_map["instructor"].id),
            OrganizationMember(organization_id=brigada.id, user_id=student.id, role_id=role_map["student"].id),
        ]
    )

    comp_triage = Competency(
        organization_id=brigada.id,
        code="RES-START-01",
        title="Evaluación de escena, bioseguridad y triaje START",
        education_level="rescue",
    )
    db.add(comp_triage)
    db.flush()

    program = Program(
        organization_id=brigada.id,
        code="PROG-RES-BAS",
        title="Formación Inicial de Brigadista de Rescate",
        description="Programa oficial piloto de respuesta primaria y soporte vital básico.",
        education_level="rescue",
    )
    db.add(program)
    db.flush()

    cv = CurriculumVersion(
        organization_id=brigada.id,
        program_id=program.id,
        version_number=1,
        title="Pensum Brigada Alfa 2026 v1",
        passing_score=Decimal("80.00"),
        status="published",
        published_at=datetime.now(timezone.utc),
        created_by=coordinator.id,
    )
    db.add(cv)
    db.flush()

    inst_course = Course(
        organization_id=brigada.id,
        title="Seguridad en Escena y Triaje START",
        slug="seguridad-escena-triaje",
        description="Protocolos prácticos de evaluación segura, control de hemorragias y clasificación START.",
        education_level="rescue",
        ui_profile="pro",
        visibility="institutional",
        status="published",
        created_by=instructor.id,
    )
    public_course = Course(
        organization_id=None,
        title="Primeros Auxilios Ciudadanos (Estudio Libre)",
        slug="primeros-auxilios-ciudadanos",
        description="Curso público abierto para reconocer emergencias cotidianas y activar ayuda segura.",
        education_level="specialized",
        ui_profile="youth",
        visibility="public",
        status="published",
        created_by=superadmin.id,
    )
    db.add_all([inst_course, public_course])
    db.flush()

    db.add(
        CurriculumUnit(
            organization_id=brigada.id,
            curriculum_version_id=cv.id,
            course_id=inst_course.id,
            primary_competency_id=comp_triage.id,
            unit_code="U-01",
            title="Unidad 1: Seguridad y Valoración Primaria",
            order_index=1,
        )
    )

    classroom = Classroom(
        organization_id=brigada.id,
        curriculum_version_id=cv.id,
        code="COHORTE-ALFA-2026",
        name="Cohorte Piloto Rescate Urbano A",
        energy_enabled=False,
    )
    db.add(classroom)
    db.flush()

    db.add(
        InstructorAssignment(
            organization_id=brigada.id,
            classroom_id=classroom.id,
            instructor_user_id=instructor.id,
            is_lead=True,
        )
    )
    db.add(
        ClassroomMember(
            organization_id=brigada.id,
            classroom_id=classroom.id,
            user_id=student.id,
        )
    )

    # Módulo + Lección piloto con los 6 tipos de retos
    mod_inst = Module(course_id=inst_course.id, title="Módulo 1: Escena Segura y Respuesta", order_index=1)
    mod_pub = Module(course_id=public_course.id, title="Módulo 1: Llamada de Emergencia", order_index=1)
    db.add_all([mod_inst, mod_pub])
    db.flush()

    les_inst = Lesson(
        module_id=mod_inst.id,
        title="Protocolo Integral de Primer Contacto",
        slug="protocolo-primer-contacto",
        order_index=1,
        estimated_minutes=8,
        is_safety_critical=True,
    )
    les_pub = Lesson(
        module_id=mod_pub.id,
        title="¿Qué informar al número de emergencias?",
        slug="que-informar-emergencias",
        order_index=1,
        estimated_minutes=4,
        is_safety_critical=False,
    )
    db.add_all([les_inst, les_pub])
    db.flush()

    lv_inst = LessonVersion(
        lesson_id=les_inst.id,
        version_number=1,
        summary="Versión piloto con 6 tipos de retos interactivos de rescate.",
        status="published",
        published_by=instructor.id,
        published_at=datetime.now(timezone.utc),
    )
    lv_pub = LessonVersion(
        lesson_id=les_pub.id,
        version_number=1,
        summary="Lección pública de estudio libre.",
        status="published",
        published_by=superadmin.id,
        published_at=datetime.now(timezone.utc),
    )
    db.add_all([lv_inst, lv_pub])
    db.flush()

    challenges_inst = [
        Challenge(
            lesson_version_id=lv_inst.id,
            competency_id=comp_triage.id,
            challenge_type="visual_concept_card",
            order_index=1,
            prompt="Revisa el concepto clave sobre Posición Lateral de Seguridad (PLS).",
            payload_json={
                "card_title": "Posición Lateral de Seguridad (PLS)",
                "visual_caption": "Mantiene permeable la vía aérea en pacientes inconscientes que respiran sin trauma.",
                "key_points": [
                    "Evita obstrucción por caída de la lengua o vómito.",
                    "Contraindicada ante sospecha de lesión cervical o de columna.",
                ],
                "check_question": {
                    "question": "¿En cuál situación NO debes colocar inmediatamente al paciente en PLS?",
                    "options": [
                        {"id": "a", "text": "Paciente inconsciente que respira tras desmayo simple"},
                        {"id": "b", "text": "Accidente de motocicleta con sospecha de trauma cervical"},
                        {"id": "c", "text": "Paciente que vomita sin trauma reportado"},
                    ],
                },
            },
            answer_key_json={"correct_option_id": "b"},
            pedagogical_explanation="Ante sospecha de trauma cervical se debe priorizar la estabilización alineada de columna.",
            difficulty=2,
            points=10,
            is_safety_critical=True,
            status="published",
        ),
        Challenge(
            lesson_version_id=lv_inst.id,
            competency_id=comp_triage.id,
            challenge_type="matching",
            order_index=2,
            prompt="Relaciona cada color de triaje START con su significado operativo.",
            payload_json={
                "instruction": "Empareja color con prioridad de atención.",
                "left_items": [
                    {"id": "l1", "text": "Rojo"},
                    {"id": "l2", "text": "Amarillo"},
                    {"id": "l3", "text": "Verde"},
                ],
                "right_items": [
                    {"id": "r1", "text": "Atención diferida (lesiones moderadas estables)"},
                    {"id": "r2", "text": "Prioridad inmediata (compromiso vital)"},
                    {"id": "r3", "text": "Lesiones leves (paciente deambula)"},
                ],
                "shuffle": True,
            },
            answer_key_json={"pairs": {"l1": "r2", "l2": "r1", "l3": "r3"}},
            pedagogical_explanation="START clasifica Rojo como inmediato, Amarillo como diferido y Verde como menor.",
            difficulty=2,
            points=15,
            is_safety_critical=True,
            status="published",
        ),
        Challenge(
            lesson_version_id=lv_inst.id,
            competency_id=comp_triage.id,
            challenge_type="sequence_ordering",
            order_index=3,
            prompt="Ordena los pasos iniciales para controlar una hemorragia severa en extremidad.",
            payload_json={
                "instruction": "Coloca los pasos en orden estricto de ejecución.",
                "items": [
                    {"id": "s1", "text": "Aplicar presión directa firme con apósito limpio"},
                    {"id": "s2", "text": "Colocar torniquete 5-7 cm sobre la herida si no cede"},
                    {"id": "s3", "text": "Colocarse guantes de nitrilo (EPP)"},
                ],
            },
            answer_key_json={"expected_order": ["s3", "s1", "s2"]},
            pedagogical_explanation="La bioseguridad (EPP) precede al contacto; luego presión directa y torniquete si la hemorragia exsanguinante persiste.",
            difficulty=2,
            points=15,
            is_safety_critical=True,
            status="published",
        ),
        Challenge(
            lesson_version_id=lv_inst.id,
            competency_id=comp_triage.id,
            challenge_type="interactive_zones",
            order_index=4,
            prompt="Selecciona la zona correcta para verificar el pulso carotídeo en un adulto inconsciente.",
            payload_json={
                "instruction": "Haz clic o selecciona la zona anatómica correcta en el esquema.",
                "diagram_svg_preset": "neck_carotid_v1",
                "aspect_ratio": "16:9",
                "selection_mode": "single",
                "zones": [
                    {"id": "z_trachea", "shape": "circle", "x": 0.50, "y": 0.48, "r": 0.08, "label": "Tráquea (línea media)"},
                    {"id": "z_carotid", "shape": "circle", "x": 0.39, "y": 0.48, "r": 0.07, "label": "Surco carotídeo lateral"},
                    {"id": "z_clavicle", "shape": "rect", "x": 0.30, "y": 0.72, "w": 0.40, "h": 0.12, "label": "Clavícula"},
                ],
            },
            answer_key_json={"correct_zone_ids": ["z_carotid"], "accept_coordinates_within_zones": True},
            pedagogical_explanation="El pulso carotídeo se palpa con dos dedos en el surco lateral del cuello, nunca comprimiendo ambos lados ni sobre la tráquea.",
            difficulty=3,
            points=15,
            is_safety_critical=True,
            status="published",
        ),
        Challenge(
            lesson_version_id=lv_inst.id,
            competency_id=comp_triage.id,
            challenge_type="decision_simulation",
            order_index=5,
            prompt="Simulación táctica: incidente nocturno con fuga de combustible.",
            payload_json={
                "scenario_context": "Llegas a un choque vehicular. Hay olor intenso a gasolina y el conductor está consciente refiriendo dolor de cuello.",
                "initial_node_id": "n1",
                "nodes": {
                    "n1": {
                        "narrative": "¿Cuál es tu primera decisión al bajar de la unidad?",
                        "choices": [
                            {"id": "c1", "text": "Extraer al conductor de inmediato jalando de sus hombros", "next_node_id": "end_unsafe"},
                            {"id": "c2", "text": "Asegurar perímetro, eliminar fuentes de ignición y solicitar bomberos", "next_node_id": "n2"},
                        ],
                    },
                    "n2": {
                        "narrative": "El perímetro está asegurado y sin chispas activas. El paciente sigue alerta con dolor cervical.",
                        "choices": [
                            {"id": "c3", "text": "Mantener estabilización cervical manual y valorar vía aérea", "next_node_id": "end_safe"},
                            {"id": "c4", "text": "Pedirle que camine hacia la ambulancia", "next_node_id": "end_unsafe_move"},
                        ],
                    },
                    "end_safe": {"is_terminal": True, "summary": "Intervención segura completada."},
                    "end_unsafe": {"is_terminal": True, "summary": "Riesgo grave de explosión y lesión medular."},
                    "end_unsafe_move": {"is_terminal": True, "summary": "Movilización contraindicada ante dolor cervical."},
                },
            },
            answer_key_json={"optimal_paths": [["c2", "c3"]], "acceptable_terminal_nodes": ["end_safe"]},
            pedagogical_explanation="Primero se controla el riesgo de escena (combustible/ignición) y luego se inmoviliza la columna cervical sin movilizaciones innecesarias.",
            difficulty=3,
            points=20,
            is_safety_critical=True,
            status="published",
        ),
        Challenge(
            lesson_version_id=lv_inst.id,
            competency_id=comp_triage.id,
            challenge_type="fill_in_blanks",
            order_index=6,
            prompt="Completa los parámetros de RCP de alta calidad en adultos.",
            payload_json={
                "template": "En RCP de un solo reanimador se realizan {{b1}} compresiones por {{b2}} ventilaciones, comprimiendo a una profundidad de {{b3}} cm.",
                "input_mode": "word_bank",
                "word_bank": ["15", "30", "2", "5 a 6", "1 a 2"],
                "blanks": [
                    {"id": "b1", "label": "Compresiones"},
                    {"id": "b2", "label": "Ventilaciones"},
                    {"id": "b3", "label": "Profundidad (cm)"},
                ],
            },
            answer_key_json={
                "blanks": {
                    "b1": {"accepted": ["30"], "case_sensitive": False},
                    "b2": {"accepted": ["2"], "case_sensitive": False},
                    "b3": {"accepted": ["5 a 6", "5-6"], "case_sensitive": False},
                }
            },
            pedagogical_explanation="La relación estándar de RCP adulto es 30:2 con profundidad de 5 a 6 cm permitiendo reexpansión torácica completa.",
            difficulty=2,
            points=15,
            is_safety_critical=True,
            status="published",
        ),
    ]

    public_challenge = Challenge(
        lesson_version_id=lv_pub.id,
        challenge_type="sequence_ordering",
        order_index=1,
        prompt="Ordena la información esencial al llamar al servicio de emergencias.",
        payload_json={
            "instruction": "Prioriza los datos para que la ambulancia salga rápido.",
            "items": [
                {"id": "p1", "text": "Ubicación exacta y referencias del lugar"},
                {"id": "p2", "text": "Número de personas afectadas y estado aparente"},
                {"id": "p3", "text": "Tu nombre y no colgar hasta que el operador lo indique"},
            ],
        },
        answer_key_json={"expected_order": ["p1", "p2", "p3"]},
        pedagogical_explanation="La ubicación exacta permite despachar la unidad de inmediato incluso si se corta la llamada.",
        difficulty=1,
        points=10,
        is_safety_critical=False,
        status="published",
    )

    db.add_all([*challenges_inst, public_challenge])
    db.flush()

    badge_first = Badge(
        organization_id=None,
        code="FIRST_RESCUE_LESSON",
        name="Primera Guardia Completada",
        description="Completa tu primera lección operativa sin omitir protocolos críticos.",
        criteria_json={"type": "lesson_completed", "min_score_pct": 80},
    )
    media_pls = MediaAsset(
        organization_id=brigada.id,
        competency_id=comp_triage.id,
        uploaded_by=instructor.id,
        title="Esquema Posición Lateral de Seguridad (PLS)",
        description="Guía visual paso a paso para permeabilizar vía aérea sin trauma cervical.",
        tags_json=["rescate", "via-aerea", "pls"],
        education_level="rescue",
        visibility="institutional",
        media_format="svg",
        mime_type="image/svg+xml",
        storage_key=f"orgs/{brigada.id}/pls_seed.svg",
        byte_size=1024,
        processing_status="ready",
    )
    media_start = MediaAsset(
        organization_id=brigada.id,
        competency_id=comp_triage.id,
        uploaded_by=instructor.id,
        title="Tarjeta Flash: Código de Colores Triaje START",
        description="Clasificación rápida Rojo, Amarillo, Verde y Negro en incidentes con múltiples víctimas.",
        tags_json=["triaje", "start", "emergencias"],
        education_level="rescue",
        visibility="institutional",
        media_format="svg",
        mime_type="image/svg+xml",
        storage_key=f"orgs/{brigada.id}/start_seed.svg",
        byte_size=1024,
        processing_status="ready",
    )
    db.add_all([badge_first, media_pls, media_start])
    db.flush()

    db.add_all(
        [
            ChallengeMediaAsset(
                challenge_id=challenges_inst[0].id,
                media_asset_id=media_pls.id,
                role="primary",
                order_index=0,
            ),
            ChallengeMediaAsset(
                challenge_id=challenges_inst[1].id,
                media_asset_id=media_start.id,
                role="primary",
                order_index=0,
            ),
        ]
    )
    db.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed_database(session)
        print("Seed piloto ejecutado correctamente.")
