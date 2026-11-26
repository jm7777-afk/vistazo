# Vistazo LMS — Plataforma Educativa Gamificada, Visual y Multiinstitucional

Plataforma LMS modular con aislamiento multi-tenant estricto, modo institucional y modo estudio libre, motor extensible de retos interactivos, repetición espaciada, biblioteca visual, asistente pedagógico IA y certificación digital verificable.

## Estado del proyecto — Fase 1 (MVP Piloto Brigada de Rescate)

Implementación actual de **Fase 1**:
- **Backend (`FastAPI` + `SQLAlchemy 2.x` + `Alembic` + `PostgreSQL`)**:
  - Autenticación segura (JWT access token de corta duración + refresh token opaco rotativo con detección de reuso y protección CSRF).
  - Arquitectura multi-tenant (`Shared Schema` con `organization_id` obligatorio en endpoints institucionales) + Modo Estudio Libre (`organization_id IS NULL`, `visibility = 'public'`).
  - RBAC granular (`super_admin`, `coordinator`, `instructor`, `student` + permisos granulares y auditoría en `audit_logs`).
  - Programas formativos, versiones inmutables de pensum (`curriculum_versions`), aulas (`classrooms`), matrículas (`classroom_members`) y asignación de instructores (`instructor_assignments`).
  - Cursos públicos e institucionales, módulos, lecciones con versionado inmutable (`lesson_versions`).
  - Motor extensible de los **6 tipos de retos**: `visual_concept_card`, `matching`, `sequence_ordering`, `interactive_zones`, `decision_simulation`, `fill_in_blanks` con validación Pydantic y evaluación exclusivamente en backend.
  - Progreso por estudiante, aula y versión de lección + competencias acumuladas.
- **Frontend (`React` + `TypeScript` + `Vite` + `Tailwind CSS` + `TanStack Query` + `PWA`)**:
  - Diseño Mobile-First con adaptación a 3 perfiles visuales (`kids`, `youth`, `pro`).
  - Catálogo público de estudio libre, login/registro, selector de organización, dashboards por rol (Estudiante, Instructor, Coordinador, SuperAdmin), mapa de aprendizaje, reproductor interactivo de los 6 retos y estados completos (carga, error, vacío, éxito).

## Inicio rápido con Docker

```bash
docker compose up --build
```

## Desarrollo local (sin Docker)

### Backend
```bash
cd backend
cp .env.example .env
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

### Pruebas Backend
```bash
cd backend
pytest
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
