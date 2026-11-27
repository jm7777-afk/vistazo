"""Endpoints multi-tenant para competencias, programas, pensums y aulas."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_tenant_context, require_permission
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationDomainError
from app.db.session import get_db
from app.modules.audit.service import record_audit_log
from app.modules.auth.models import User
from app.modules.courses.models import Course
from app.modules.curriculum.models import (
    Classroom,
    ClassroomMember,
    Competency,
    CurriculumUnit,
    CurriculumVersion,
    InstructorAssignment,
    Program,
)
from app.modules.curriculum.schemas import (
    AssignInstructorRequest,
    ClassroomCreate,
    ClassroomOut,
    ClassroomStudentOut,
    ClassroomUpdate,
    CompetencyCreate,
    CompetencyOut,
    CompetencyUpdate,
    CurriculumUnitCreate,
    CurriculumUnitOut,
    CurriculumVersionCreate,
    CurriculumVersionOut,
    CurriculumVersionUpdate,
    EnrollStudentRequest,
    ProgramCreate,
    ProgramOut,
    ProgramUpdate,
)
from app.modules.progress.models import LessonProgress
from app.modules.rbac.models import Role
from app.modules.tenants.models import OrganizationMember

router = APIRouter(prefix="/orgs/{org_id}", tags=["curriculum"])


def _ensure_classroom_access(db: Session, tenant: TenantContext, classroom_id: uuid.UUID) -> Classroom:
    """Valida pertenencia de aula al tenant y alcance del instructor/coordinador."""
    classroom = db.scalar(
        select(Classroom).where(
            Classroom.id == classroom_id,
            Classroom.organization_id == tenant.organization.id,
            Classroom.deleted_at.is_(None),
        )
    )
    if not classroom:
        raise NotFoundError("Aula no encontrada en esta organización")

    if tenant.has_permission("classroom:manage"):
        return classroom

    if "instructor" in tenant.role_codes:
        assigned = db.scalar(
            select(InstructorAssignment).where(
                InstructorAssignment.classroom_id == classroom.id,
                InstructorAssignment.organization_id == tenant.organization.id,
                InstructorAssignment.instructor_user_id == tenant.user.id,
                InstructorAssignment.deleted_at.is_(None),
            )
        )
        if not assigned:
            raise ForbiddenError("No estás asignado como instructor de esta aula")
        return classroom

    enrolled = db.scalar(
        select(ClassroomMember).where(
            ClassroomMember.classroom_id == classroom.id,
            ClassroomMember.organization_id == tenant.organization.id,
            ClassroomMember.user_id == tenant.user.id,
            ClassroomMember.deleted_at.is_(None),
        )
    )
    if not enrolled:
        raise ForbiddenError("No estás matriculado en esta aula")
    return classroom


@router.get("/competencies", response_model=list[CompetencyOut])
def list_competencies(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> list[CompetencyOut]:
    rows = db.scalars(
        select(Competency).where(
            Competency.deleted_at.is_(None),
            (Competency.organization_id == tenant.organization.id) | (Competency.organization_id.is_(None)),
        )
    ).all()
    return [
        CompetencyOut(
            id=c.id,
            organization_id=c.organization_id,
            code=c.code,
            title=c.title,
            description=c.description,
            education_level=c.education_level,
        )
        for c in rows
    ]


@router.post("/competencies", response_model=CompetencyOut, status_code=status.HTTP_201_CREATED)
def create_competency(
    payload: CompetencyCreate,
    tenant: TenantContext = Depends(require_permission("curriculum:manage")),
    db: Session = Depends(get_db),
) -> CompetencyOut:
    dup = db.scalar(
        select(Competency).where(
            Competency.organization_id == tenant.organization.id,
            func.lower(Competency.code) == payload.code.strip().lower(),
            Competency.deleted_at.is_(None),
        )
    )
    if dup:
        raise ConflictError("El código de competencia ya existe en la organización")
    comp = Competency(
        organization_id=tenant.organization.id,
        code=payload.code.strip(),
        title=payload.title.strip(),
        description=payload.description,
        education_level=payload.education_level,
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return CompetencyOut(
        id=comp.id,
        organization_id=comp.organization_id,
        code=comp.code,
        title=comp.title,
        description=comp.description,
        education_level=comp.education_level,
    )


@router.patch("/competencies/{competency_id}", response_model=CompetencyOut)
def update_competency(
    competency_id: uuid.UUID,
    payload: CompetencyUpdate,
    tenant: TenantContext = Depends(require_permission("curriculum:manage")),
    db: Session = Depends(get_db),
) -> CompetencyOut:
    comp = db.scalar(
        select(Competency).where(
            Competency.id == competency_id,
            Competency.organization_id == tenant.organization.id,
            Competency.deleted_at.is_(None),
        )
    )
    if not comp:
        raise NotFoundError("Competencia no encontrada en esta organización")
    if payload.title is not None:
        comp.title = payload.title.strip()
    if payload.description is not None:
        comp.description = payload.description
    if payload.education_level is not None:
        comp.education_level = payload.education_level
    db.commit()
    db.refresh(comp)
    return CompetencyOut(
        id=comp.id,
        organization_id=comp.organization_id,
        code=comp.code,
        title=comp.title,
        description=comp.description,
        education_level=comp.education_level,
    )


@router.delete("/competencies/{competency_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_competency(
    competency_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("curriculum:manage")),
    db: Session = Depends(get_db),
) -> Response:
    comp = db.scalar(
        select(Competency).where(
            Competency.id == competency_id,
            Competency.organization_id == tenant.organization.id,
            Competency.deleted_at.is_(None),
        )
    )
    if not comp:
        raise NotFoundError("Competencia no encontrada en esta organización")
    comp.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/programs", response_model=list[ProgramOut])
def list_programs(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> list[ProgramOut]:
    rows = db.scalars(
        select(Program)
        .where(Program.organization_id == tenant.organization.id, Program.deleted_at.is_(None))
        .order_by(Program.created_at.desc())
    ).all()
    return [
        ProgramOut(
            id=p.id,
            organization_id=p.organization_id,
            code=p.code,
            title=p.title,
            description=p.description,
            education_level=p.education_level,
            is_active=p.is_active,
        )
        for p in rows
    ]


@router.post("/programs", response_model=ProgramOut, status_code=status.HTTP_201_CREATED)
def create_program(
    payload: ProgramCreate,
    tenant: TenantContext = Depends(require_permission("curriculum:manage")),
    db: Session = Depends(get_db),
) -> ProgramOut:
    dup = db.scalar(
        select(Program).where(
            Program.organization_id == tenant.organization.id,
            func.lower(Program.code) == payload.code.strip().lower(),
            Program.deleted_at.is_(None),
        )
    )
    if dup:
        raise ConflictError("Ya existe un programa con ese código en la organización")
    prog = Program(
        organization_id=tenant.organization.id,
        code=payload.code.strip(),
        title=payload.title.strip(),
        description=payload.description,
        education_level=payload.education_level,
    )
    db.add(prog)
    db.commit()
    db.refresh(prog)
    return ProgramOut(
        id=prog.id,
        organization_id=prog.organization_id,
        code=prog.code,
        title=prog.title,
        description=prog.description,
        education_level=prog.education_level,
        is_active=prog.is_active,
    )


@router.patch("/programs/{program_id}", response_model=ProgramOut)
def update_program(
    program_id: uuid.UUID,
    payload: ProgramUpdate,
    tenant: TenantContext = Depends(require_permission("curriculum:manage")),
    db: Session = Depends(get_db),
) -> ProgramOut:
    prog = db.scalar(
        select(Program).where(
            Program.id == program_id,
            Program.organization_id == tenant.organization.id,
            Program.deleted_at.is_(None),
        )
    )
    if not prog:
        raise NotFoundError("Programa no encontrado en esta organización")
    if payload.title is not None:
        prog.title = payload.title.strip()
    if payload.description is not None:
        prog.description = payload.description
    if payload.education_level is not None:
        prog.education_level = payload.education_level
    if payload.is_active is not None:
        prog.is_active = payload.is_active
    db.commit()
    db.refresh(prog)
    return ProgramOut(
        id=prog.id,
        organization_id=prog.organization_id,
        code=prog.code,
        title=prog.title,
        description=prog.description,
        education_level=prog.education_level,
        is_active=prog.is_active,
    )


@router.delete("/programs/{program_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_program(
    program_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("curriculum:manage")),
    db: Session = Depends(get_db),
) -> Response:
    prog = db.scalar(
        select(Program).where(
            Program.id == program_id,
            Program.organization_id == tenant.organization.id,
            Program.deleted_at.is_(None),
        )
    )
    if not prog:
        raise NotFoundError("Programa no encontrado en esta organización")
    prog.deleted_at = datetime.now(timezone.utc)
    prog.deleted_by = tenant.user.id
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/programs/{program_id}/curriculum-versions", response_model=list[CurriculumVersionOut])
def list_curriculum_versions(
    program_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> list[CurriculumVersionOut]:
    versions = db.scalars(
        select(CurriculumVersion)
        .where(
            CurriculumVersion.program_id == program_id,
            CurriculumVersion.organization_id == tenant.organization.id,
        )
        .order_by(CurriculumVersion.version_number.desc())
    ).all()
    result: list[CurriculumVersionOut] = []
    for cv in versions:
        units = db.scalars(
            select(CurriculumUnit)
            .where(CurriculumUnit.curriculum_version_id == cv.id)
            .order_by(CurriculumUnit.order_index)
        ).all()
        result.append(
            CurriculumVersionOut(
                id=cv.id,
                program_id=cv.program_id,
                version_number=cv.version_number,
                title=cv.title,
                passing_score=cv.passing_score,
                status=cv.status,
                published_at=cv.published_at,
                units=[
                    CurriculumUnitOut(
                        id=u.id,
                        course_id=u.course_id,
                        primary_competency_id=u.primary_competency_id,
                        unit_code=u.unit_code,
                        title=u.title,
                        order_index=u.order_index,
                        is_mandatory=u.is_mandatory,
                        weight=u.weight,
                    )
                    for u in units
                ],
            )
        )
    return result


@router.post("/programs/{program_id}/curriculum-versions", response_model=CurriculumVersionOut, status_code=status.HTTP_201_CREATED)
def create_curriculum_version(
    program_id: uuid.UUID,
    payload: CurriculumVersionCreate,
    tenant: TenantContext = Depends(require_permission("curriculum:manage")),
    db: Session = Depends(get_db),
) -> CurriculumVersionOut:
    program = db.scalar(
        select(Program).where(
            Program.id == program_id,
            Program.organization_id == tenant.organization.id,
            Program.deleted_at.is_(None),
        )
    )
    if not program:
        raise NotFoundError("Programa no encontrado en esta organización")

    max_ver = db.scalar(
        select(func.coalesce(func.max(CurriculumVersion.version_number), 0)).where(
            CurriculumVersion.program_id == program.id
        )
    )
    cv = CurriculumVersion(
        organization_id=tenant.organization.id,
        program_id=program.id,
        version_number=int(max_ver or 0) + 1,
        title=payload.title.strip(),
        passing_score=payload.passing_score,
        created_by=tenant.user.id,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return CurriculumVersionOut(
        id=cv.id,
        program_id=cv.program_id,
        version_number=cv.version_number,
        title=cv.title,
        passing_score=cv.passing_score,
        status=cv.status,
        published_at=cv.published_at,
        units=[],
    )


@router.post("/curriculum-versions/{cv_id}/units", response_model=CurriculumUnitOut, status_code=status.HTTP_201_CREATED)
def add_curriculum_unit(
    cv_id: uuid.UUID,
    payload: CurriculumUnitCreate,
    tenant: TenantContext = Depends(require_permission("curriculum:manage")),
    db: Session = Depends(get_db),
) -> CurriculumUnitOut:
    cv = db.scalar(
        select(CurriculumVersion).where(
            CurriculumVersion.id == cv_id,
            CurriculumVersion.organization_id == tenant.organization.id,
        )
    )
    if not cv:
        raise NotFoundError("Versión de pensum no encontrada")
    if cv.status != "draft":
        raise ValidationDomainError("Solo se pueden modificar unidades de un pensum en borrador")

    course = db.scalar(
        select(Course).where(
            Course.id == payload.course_id,
            Course.deleted_at.is_(None),
            (Course.organization_id == tenant.organization.id) | (Course.visibility == "public"),
        )
    )
    if not course:
        raise NotFoundError("Curso no válido o inaccesible para esta organización")

    unit = CurriculumUnit(
        organization_id=tenant.organization.id,
        curriculum_version_id=cv.id,
        course_id=course.id,
        primary_competency_id=payload.primary_competency_id,
        unit_code=payload.unit_code.strip(),
        title=payload.title.strip(),
        order_index=payload.order_index,
        is_mandatory=payload.is_mandatory,
        weight=payload.weight,
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return CurriculumUnitOut(
        id=unit.id,
        course_id=unit.course_id,
        primary_competency_id=unit.primary_competency_id,
        unit_code=unit.unit_code,
        title=unit.title,
        order_index=unit.order_index,
        is_mandatory=unit.is_mandatory,
        weight=unit.weight,
    )


@router.patch("/curriculum-versions/{cv_id}", response_model=CurriculumVersionOut)
def update_curriculum_version(
    cv_id: uuid.UUID,
    payload: CurriculumVersionUpdate,
    tenant: TenantContext = Depends(require_permission("curriculum:manage")),
    db: Session = Depends(get_db),
) -> CurriculumVersionOut:
    cv = db.scalar(
        select(CurriculumVersion).where(
            CurriculumVersion.id == cv_id,
            CurriculumVersion.organization_id == tenant.organization.id,
        )
    )
    if not cv:
        raise NotFoundError("Versión de pensum no encontrada")
    if payload.title is not None:
        cv.title = payload.title.strip()
    if payload.passing_score is not None:
        cv.passing_score = payload.passing_score
    if payload.status is not None:
        cv.status = payload.status
    db.commit()
    db.refresh(cv)
    units = db.scalars(
        select(CurriculumUnit)
        .where(CurriculumUnit.curriculum_version_id == cv.id)
        .order_by(CurriculumUnit.order_index)
    ).all()
    return CurriculumVersionOut(
        id=cv.id,
        program_id=cv.program_id,
        version_number=cv.version_number,
        title=cv.title,
        passing_score=cv.passing_score,
        status=cv.status,
        published_at=cv.published_at,
        units=[
            CurriculumUnitOut(
                id=u.id,
                course_id=u.course_id,
                primary_competency_id=u.primary_competency_id,
                unit_code=u.unit_code,
                title=u.title,
                order_index=u.order_index,
                is_mandatory=u.is_mandatory,
                weight=u.weight,
            )
            for u in units
        ],
    )


@router.delete("/curriculum-units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_curriculum_unit(
    unit_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("curriculum:manage")),
    db: Session = Depends(get_db),
) -> Response:
    row = db.execute(
        select(CurriculumUnit, CurriculumVersion)
        .join(CurriculumVersion, CurriculumUnit.curriculum_version_id == CurriculumVersion.id)
        .where(
            CurriculumUnit.id == unit_id,
            CurriculumUnit.organization_id == tenant.organization.id,
        )
    ).first()
    if not row:
        raise NotFoundError("Unidad de pensum no encontrada")
    unit, cv = row
    if cv.status != "draft":
        raise ValidationDomainError("Solo se pueden eliminar unidades de un pensum en borrador")
    db.delete(unit)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/curriculum-versions/{cv_id}/publish", response_model=CurriculumVersionOut)
def publish_curriculum_version(
    cv_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("curriculum:manage")),
    db: Session = Depends(get_db),
) -> CurriculumVersionOut:
    cv = db.scalar(
        select(CurriculumVersion).where(
            CurriculumVersion.id == cv_id,
            CurriculumVersion.organization_id == tenant.organization.id,
        )
    )
    if not cv:
        raise NotFoundError("Versión de pensum no encontrada")

    units = db.scalars(
        select(CurriculumUnit)
        .where(CurriculumUnit.curriculum_version_id == cv.id)
        .order_by(CurriculumUnit.order_index)
    ).all()
    if not units:
        raise ValidationDomainError("Un pensum debe tener al menos una unidad antes de publicarse")

    cv.status = "published"
    cv.published_at = datetime.now(timezone.utc)
    record_audit_log(
        db,
        action="curriculum_version.published",
        resource_type="curriculum_version",
        resource_id=cv.id,
        organization_id=tenant.organization.id,
        actor_user_id=tenant.user.id,
    )
    db.commit()
    return CurriculumVersionOut(
        id=cv.id,
        program_id=cv.program_id,
        version_number=cv.version_number,
        title=cv.title,
        passing_score=cv.passing_score,
        status=cv.status,
        published_at=cv.published_at,
        units=[
            CurriculumUnitOut(
                id=u.id,
                course_id=u.course_id,
                primary_competency_id=u.primary_competency_id,
                unit_code=u.unit_code,
                title=u.title,
                order_index=u.order_index,
                is_mandatory=u.is_mandatory,
                weight=u.weight,
            )
            for u in units
        ],
    )


@router.get("/classrooms", response_model=list[ClassroomOut])
def list_classrooms(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
) -> list[ClassroomOut]:
    """Lista aulas según rol: coordinador todas; instructor solo asignadas; estudiante solo matriculadas."""
    base_stmt = select(Classroom).where(
        Classroom.organization_id == tenant.organization.id,
        Classroom.deleted_at.is_(None),
    )

    if tenant.has_permission("classroom:manage"):
        rows = db.scalars(base_stmt.order_by(Classroom.created_at.desc())).all()
    elif "instructor" in tenant.role_codes:
        rows = db.scalars(
            base_stmt.join(InstructorAssignment, InstructorAssignment.classroom_id == Classroom.id)
            .where(
                InstructorAssignment.instructor_user_id == tenant.user.id,
                InstructorAssignment.deleted_at.is_(None),
            )
            .order_by(Classroom.created_at.desc())
        ).all()
    else:
        rows = db.scalars(
            base_stmt.join(ClassroomMember, ClassroomMember.classroom_id == Classroom.id)
            .where(
                ClassroomMember.user_id == tenant.user.id,
                ClassroomMember.deleted_at.is_(None),
                ClassroomMember.enrollment_status == "enrolled",
            )
            .order_by(Classroom.created_at.desc())
        ).all()

    return [
        ClassroomOut(
            id=c.id,
            organization_id=c.organization_id,
            curriculum_version_id=c.curriculum_version_id,
            code=c.code,
            name=c.name,
            starts_at=c.starts_at,
            ends_at=c.ends_at,
            energy_enabled=c.energy_enabled,
            max_energy=c.max_energy,
            status=c.status,
        )
        for c in rows
    ]


@router.post("/classrooms", response_model=ClassroomOut, status_code=status.HTTP_201_CREATED)
def create_classroom(
    payload: ClassroomCreate,
    tenant: TenantContext = Depends(require_permission("classroom:manage")),
    db: Session = Depends(get_db),
) -> ClassroomOut:
    cv = db.scalar(
        select(CurriculumVersion).where(
            CurriculumVersion.id == payload.curriculum_version_id,
            CurriculumVersion.organization_id == tenant.organization.id,
        )
    )
    if not cv or cv.status != "published":
        raise ValidationDomainError("El aula debe asociarse a una versión de pensum publicada de esta organización")

    dup = db.scalar(
        select(Classroom).where(
            Classroom.organization_id == tenant.organization.id,
            func.lower(Classroom.code) == payload.code.strip().lower(),
            Classroom.deleted_at.is_(None),
        )
    )
    if dup:
        raise ConflictError("Ya existe un aula con ese código")

    classroom = Classroom(
        organization_id=tenant.organization.id,
        curriculum_version_id=cv.id,
        code=payload.code.strip(),
        name=payload.name.strip(),
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        energy_enabled=payload.energy_enabled,
        max_energy=payload.max_energy,
    )
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return ClassroomOut(
        id=classroom.id,
        organization_id=classroom.organization_id,
        curriculum_version_id=classroom.curriculum_version_id,
        code=classroom.code,
        name=classroom.name,
        starts_at=classroom.starts_at,
        ends_at=classroom.ends_at,
        energy_enabled=classroom.energy_enabled,
        max_energy=classroom.max_energy,
        status=classroom.status,
    )


@router.patch("/classrooms/{classroom_id}", response_model=ClassroomOut)
def update_classroom(
    classroom_id: uuid.UUID,
    payload: ClassroomUpdate,
    tenant: TenantContext = Depends(require_permission("classroom:manage")),
    db: Session = Depends(get_db),
) -> ClassroomOut:
    classroom = _ensure_classroom_access(db, tenant, classroom_id)
    if payload.name is not None:
        classroom.name = payload.name.strip()
    if payload.energy_enabled is not None:
        classroom.energy_enabled = payload.energy_enabled
    if payload.max_energy is not None:
        classroom.max_energy = payload.max_energy
    if payload.status is not None:
        classroom.status = payload.status
    db.commit()
    db.refresh(classroom)
    return ClassroomOut(
        id=classroom.id,
        organization_id=classroom.organization_id,
        curriculum_version_id=classroom.curriculum_version_id,
        code=classroom.code,
        name=classroom.name,
        starts_at=classroom.starts_at,
        ends_at=classroom.ends_at,
        energy_enabled=classroom.energy_enabled,
        max_energy=classroom.max_energy,
        status=classroom.status,
    )


@router.delete("/classrooms/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_classroom(
    classroom_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("classroom:manage")),
    db: Session = Depends(get_db),
) -> Response:
    classroom = _ensure_classroom_access(db, tenant, classroom_id)
    classroom.deleted_at = datetime.now(timezone.utc)
    classroom.deleted_by = tenant.user.id
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/classrooms/{classroom_id}/instructors", status_code=status.HTTP_201_CREATED)
def assign_instructor(
    classroom_id: uuid.UUID,
    payload: AssignInstructorRequest,
    tenant: TenantContext = Depends(require_permission("classroom:manage")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    classroom = _ensure_classroom_access(db, tenant, classroom_id)
    user = db.scalar(
        select(User).where(User.email == payload.instructor_email.lower(), User.deleted_at.is_(None))
    )
    if not user:
        raise NotFoundError("Instructor no encontrado")

    # Asegura membresía como instructor en la organización
    inst_membership = db.scalar(
        select(OrganizationMember)
        .join(Role, OrganizationMember.role_id == Role.id)
        .where(
            OrganizationMember.organization_id == tenant.organization.id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.deleted_at.is_(None),
            Role.code.in_(["instructor", "coordinator"]),
        )
    )
    if not inst_membership:
        raise ValidationDomainError("El usuario debe tener rol de instructor o coordinador en la organización")

    existing = db.scalar(
        select(InstructorAssignment).where(
            InstructorAssignment.classroom_id == classroom.id,
            InstructorAssignment.instructor_user_id == user.id,
            InstructorAssignment.deleted_at.is_(None),
        )
    )
    if existing:
        raise ConflictError("El instructor ya está asignado a esta aula")

    db.add(
        InstructorAssignment(
            organization_id=tenant.organization.id,
            classroom_id=classroom.id,
            instructor_user_id=user.id,
            is_lead=payload.is_lead,
        )
    )
    db.commit()
    return {"status": "assigned"}


@router.post("/classrooms/{classroom_id}/enroll", status_code=status.HTTP_201_CREATED)
def enroll_student(
    classroom_id: uuid.UUID,
    payload: EnrollStudentRequest,
    tenant: TenantContext = Depends(require_permission("classroom:manage")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    classroom = _ensure_classroom_access(db, tenant, classroom_id)
    student = db.scalar(
        select(User).where(User.email == payload.student_email.lower(), User.deleted_at.is_(None))
    )
    if not student:
        raise NotFoundError("Estudiante no encontrado")

    org_member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == tenant.organization.id,
            OrganizationMember.user_id == student.id,
            OrganizationMember.deleted_at.is_(None),
            OrganizationMember.status == "active",
        )
    )
    if not org_member:
        raise ValidationDomainError("El usuario debe ser miembro activo de la organización antes de matricularse")

    existing = db.scalar(
        select(ClassroomMember).where(
            ClassroomMember.classroom_id == classroom.id,
            ClassroomMember.user_id == student.id,
            ClassroomMember.deleted_at.is_(None),
        )
    )
    if existing:
        raise ConflictError("El estudiante ya está matriculado en esta aula")

    db.add(
        ClassroomMember(
            organization_id=tenant.organization.id,
            classroom_id=classroom.id,
            user_id=student.id,
        )
    )
    db.commit()
    return {"status": "enrolled"}


@router.get("/classrooms/{classroom_id}/students", response_model=list[ClassroomStudentOut])
def list_classroom_students(
    classroom_id: uuid.UUID,
    tenant: TenantContext = Depends(require_permission("classroom:view_assigned")),
    db: Session = Depends(get_db),
) -> list[ClassroomStudentOut]:
    classroom = _ensure_classroom_access(db, tenant, classroom_id)
    rows = db.execute(
        select(ClassroomMember, User)
        .join(User, ClassroomMember.user_id == User.id)
        .where(
            ClassroomMember.classroom_id == classroom.id,
            ClassroomMember.organization_id == tenant.organization.id,
            ClassroomMember.deleted_at.is_(None),
            User.deleted_at.is_(None),
        )
        .order_by(User.full_name)
    ).all()

    output: list[ClassroomStudentOut] = []
    for member, user in rows:
        progress_rows = db.scalars(
            select(LessonProgress).where(
                LessonProgress.user_id == user.id,
                LessonProgress.classroom_id == classroom.id,
            )
        ).all()
        completed_count = sum(1 for p in progress_rows if p.status == "completed")
        avg_score = (
            round(sum(float(p.best_score_pct) for p in progress_rows) / len(progress_rows), 2)
            if progress_rows
            else 0.0
        )
        output.append(
            ClassroomStudentOut(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                enrollment_status=member.enrollment_status,
                enrolled_at=member.enrolled_at,
                completed_lessons=completed_count,
                avg_score_pct=avg_score,
            )
        )
    return output
