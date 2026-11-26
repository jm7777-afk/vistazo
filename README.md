# Vistazo LMS — Plataforma Educativa Gamificada, Visual y Multiinstitucional

Plataforma LMS modular con aislamiento multi-tenant estricto, modo institucional y modo estudio libre, motor extensible de retos interactivos, repetición espaciada, biblioteca visual, asistente pedagógico IA y certificación digital verificable.

## Estado del proyecto — Fases 1 y 2 implementadas

### Fase 1 (MVP Piloto Brigada de Rescate + Estudio Libre)
- Autenticación JWT + refresh token rotativo con detección de reuso y CSRF.
- Multi-tenancy estricto (`organization_id`) y RBAC granular con auditoría inmutable.
- Programas, versiones de pensum, aulas, matrículas, asignación de instructores, cursos públicos/institucionales y lecciones versionadas.
- Motor extensible de los **6 tipos de retos**: `visual_concept_card`, `matching`, `sequence_ordering`, `interactive_zones`, `decision_simulation`, `fill_in_blanks`.

### Fase 2 (Aprendizaje Inteligente)
- **Repetición Espaciada SM-2** (`spaced_repetition_items`, `review_sessions`) con tope de 45 días para protocolos de seguridad crítica (`is_safety_critical`) y recuperación inmediata tras errores.
- **Biblioteca Visual y Multimedia** (`media_assets`, `student_library_items`): validación MIME/tamaño, transcodificación FFmpeg (GIF→WebP/miniatura), URLs firmadas HMAC-SHA256 con expiración corta, desbloqueo automático por lección y **Modo Entrenamiento Flash**.
- **Gamificación y Analíticas**: XP, rachas diarias, energía configurable con **Biblioteca de Recuperación de Energía** (sin penalizar retos de rescate), insignias, ranking por aula y panel analítico de instructor.

### Fase 3 (IA Pedagógica)
- **Proveedores intercambiables** (`GeminiProvider`, `GroqProvider`, `DeterministicFallbackProvider`) con conmutación automática ante fallos o ausencia de API key y administración por SuperAdmin (`/api/v1/admin/ai/providers`).
- **Generador de Lecciones** (`/api/v1/orgs/{org_id}/ai/generate-lesson-draft`): crea borradores de 5–8 retos validados por Pydantic (`status='draft'`, `ai_generated=True`) sin enviar PII.
- **Tutor Socrático** (`/api/v1/challenges/{challenge_id}/socratic-hint`): habilitado tras 2 intentos fallidos, con guardrails anti-*prompt-injection*, sanitización de salidas y recordatorio obligatorio al instructor en protocolos críticos.

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
