import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BookPlus, CheckCircle2, Edit3, ExternalLink, Plus, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { EmptyState, ErrorBanner, LoadingState, SuccessBanner } from '../ui/StatusStates';
import { apiRequest } from '../../services/apiClient';
import type { CourseDetail, CourseSummary, LessonOut, LessonType, ModuleOut, UIProfile } from '../../types/api';
import { scopePrefix, slugifyText, type StudioScope } from './studioHelpers';

interface Props {
  scope: StudioScope;
  selectedCourseId: string;
  onSelectCourse: (courseId: string) => void;
  onJumpToChallenges: (courseId: string, lessonId: string) => void;
}

export function CoursesNodesTab({ scope, selectedCourseId, onSelectCourse, onJumpToChallenges }: Props) {
  const queryClient = useQueryClient();
  const prefix = scopePrefix(scope);
  const [feedback, setFeedback] = useState<string | null>(null);

  // Crear curso manual
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [level, setLevel] = useState('specialized');
  const [uiProfile, setUiProfile] = useState<UIProfile>('pro');

  // Editar curso
  const [editingCourse, setEditingCourse] = useState<CourseSummary | null>(null);

  // Crear módulo
  const [modTitle, setModTitle] = useState('');
  const [modDesc, setModDesc] = useState('');

  // Crear nodo / lección
  const [targetModuleId, setTargetModuleId] = useState('');
  const [lesTitle, setLesTitle] = useState('');
  const [lesType, setLesType] = useState<LessonType>('micro_lesson');
  const [lesMinutes, setLesMinutes] = useState(6);
  const [lesPassPct, setLesPassPct] = useState(75);
  const [lesCritical, setLesCritical] = useState(false);
  const [lesRandomize, setLesRandomize] = useState(false);
  const [lesSampleSize, setLesSampleSize] = useState('');

  const coursesQuery = useQuery({
    queryKey: ['studio-courses', prefix],
    queryFn: () => apiRequest<CourseSummary[]>(`${prefix}/courses`),
  });

  const activeCourseId = selectedCourseId || coursesQuery.data?.[0]?.id || '';

  const detailQuery = useQuery({
    queryKey: ['studio-course-detail', activeCourseId],
    queryFn: () => apiRequest<CourseDetail>(`/courses/${activeCourseId}`),
    enabled: Boolean(activeCourseId),
  });

  const createCourse = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      return apiRequest<CourseSummary>(`${prefix}/courses`, {
        method: 'POST',
        body: JSON.stringify({
          title,
          slug: `${slugifyText(title)}-${Math.floor(Math.random() * 900 + 100)}`,
          description: description || null,
          education_level: level,
          ui_profile: uiProfile,
          visibility: scope.mode === 'global' ? 'public' : 'institutional',
        }),
      });
    },
    onSuccess: (created) => {
      setTitle('');
      setDescription('');
      setFeedback(`Materia "${created.title}" creada correctamente.`);
      onSelectCourse(created.id);
      void queryClient.invalidateQueries({ queryKey: ['studio-courses', prefix] });
    },
  });

  const updateCourse = useMutation({
    mutationFn: (payload: { id: string; data: Partial<CourseSummary> }) =>
      apiRequest<CourseSummary>(`${prefix}/courses/${payload.id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload.data),
      }),
    onSuccess: (updated) => {
      setEditingCourse(null);
      setFeedback(`Materia "${updated.title}" actualizada (${updated.status}).`);
      void queryClient.invalidateQueries({ queryKey: ['studio-courses', prefix] });
      void queryClient.invalidateQueries({ queryKey: ['studio-course-detail', updated.id] });
    },
  });

  const deleteCourse = useMutation({
    mutationFn: (id: string) => apiRequest<void>(`${prefix}/courses/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      setFeedback('Materia eliminada correctamente.');
      onSelectCourse('');
      void queryClient.invalidateQueries({ queryKey: ['studio-courses', prefix] });
    },
  });

  const createModule = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      const nextOrder = (detailQuery.data?.modules.length ?? 0) + 1;
      return apiRequest<ModuleOut>(`${prefix}/courses/${activeCourseId}/modules`, {
        method: 'POST',
        body: JSON.stringify({ title: modTitle, description: modDesc || null, order_index: nextOrder }),
      });
    },
    onSuccess: () => {
      setModTitle('');
      setModDesc('');
      setFeedback('Módulo agregado al curso.');
      void queryClient.invalidateQueries({ queryKey: ['studio-course-detail', activeCourseId] });
    },
  });

  const deleteModule = useMutation({
    mutationFn: (moduleId: string) => apiRequest<void>(`${prefix}/modules/${moduleId}`, { method: 'DELETE' }),
    onSuccess: () => {
      setFeedback('Módulo eliminado.');
      void queryClient.invalidateQueries({ queryKey: ['studio-course-detail', activeCourseId] });
    },
  });

  const createLesson = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      const modId = targetModuleId || detailQuery.data?.modules[0]?.id;
      const mod = detailQuery.data?.modules.find((m) => m.id === modId);
      return apiRequest<LessonOut>(`${prefix}/modules/${modId}/lessons`, {
        method: 'POST',
        body: JSON.stringify({
          title: lesTitle,
          slug: `${slugifyText(lesTitle)}-${Math.floor(Math.random() * 900 + 100)}`,
          order_index: (mod?.lessons.length ?? 0) + 1,
          estimated_minutes: lesMinutes,
          lesson_type: lesType,
          passing_score_pct: lesPassPct,
          is_safety_critical: lesCritical,
          randomize_order: lesRandomize,
          sample_size: lesSampleSize ? Number(lesSampleSize) : null,
        }),
      });
    },
    onSuccess: () => {
      setLesTitle('');
      setFeedback('Nodo / Lección creado.');
      void queryClient.invalidateQueries({ queryKey: ['studio-course-detail', activeCourseId] });
    },
  });

  const deleteLesson = useMutation({
    mutationFn: (lessonId: string) => apiRequest<void>(`${prefix}/lessons/${lessonId}`, { method: 'DELETE' }),
    onSuccess: () => {
      setFeedback('Nodo eliminado.');
      void queryClient.invalidateQueries({ queryKey: ['studio-course-detail', activeCourseId] });
    },
  });

  const activeError =
    createCourse.error ||
    updateCourse.error ||
    deleteCourse.error ||
    createModule.error ||
    deleteModule.error ||
    createLesson.error ||
    deleteLesson.error;

  return (
    <div className="space-y-5">
      {feedback && <SuccessBanner message={feedback} />}
      {activeError && <ErrorBanner message={(activeError as Error).message} />}

      {/* Crear Materia / Curso manual */}
      <form onSubmit={createCourse.mutate} className="surface-card p-5 space-y-3">
        <h2 className="flex items-center gap-2 text-base font-bold">
          <BookPlus className="h-5 w-5 text-[var(--brand-primary)]" /> Crear Materia / Curso Manualmente ({scope.label})
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
          <input
            required
            placeholder="Título de la materia o curso"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
          />
          <select
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
          >
            <option value="primary">Primaria</option>
            <option value="secondary">Secundaria</option>
            <option value="high_school">Bachillerato</option>
            <option value="university">Universidad</option>
            <option value="technical">Técnico</option>
            <option value="specialized">Especializado</option>
            <option value="rescue">Rescate</option>
          </select>
          <select
            value={uiProfile}
            onChange={(e) => setUiProfile(e.target.value as UIProfile)}
            className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
          >
            <option value="pro">Perfil Pro</option>
            <option value="youth">Perfil Juvenil</option>
            <option value="kids">Perfil Infantil</option>
          </select>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            placeholder="Descripción breve o enfoque pedagógico..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="flex-1 rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
          />
          <button type="submit" disabled={createCourse.isPending} className="btn-primary px-5 py-2 text-xs font-bold">
            Crear Materia
          </button>
        </div>
      </form>

      {/* Listado CRUD de materias */}
      <section className="surface-card p-5 space-y-3">
        <h3 className="text-sm font-bold uppercase text-[var(--text-secondary)]">Materias y Cursos ({coursesQuery.data?.length ?? 0})</h3>
        {coursesQuery.isLoading ? (
          <LoadingState label="Cargando materias..." />
        ) : !coursesQuery.data?.length ? (
          <EmptyState title="Aún no hay materias" description="Crea una manualmente arriba o genera una completa desde el Arquitecto IA." />
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {coursesQuery.data.map((c) => {
              const selected = c.id === activeCourseId;
              return (
                <div
                  key={c.id}
                  className={`rounded-xl border p-4 space-y-2 ${
                    selected ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)]/60' : 'border-[var(--border-subtle)] bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <button type="button" onClick={() => onSelectCourse(c.id)} className="text-left">
                      <p className="font-bold text-sm">{c.title}</p>
                      <p className="text-xs text-[var(--text-secondary)]">
                        {c.education_level} • {c.ui_profile} • <strong>{c.status}</strong>
                      </p>
                    </button>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() =>
                          updateCourse.mutate({
                            id: c.id,
                            data: { status: c.status === 'published' ? 'draft' : 'published' },
                          })
                        }
                        title={c.status === 'published' ? 'Pasar a borrador' : 'Publicar curso'}
                        className="rounded border border-[var(--border-subtle)] px-2 py-1 text-[11px] font-semibold hover:bg-white"
                      >
                        <CheckCircle2 className="inline h-3.5 w-3.5 mr-1 text-emerald-600" />
                        {c.status === 'published' ? 'Publicado' : 'Publicar'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingCourse(c)}
                        className="rounded border border-[var(--border-subtle)] p-1.5 hover:bg-white"
                        aria-label="Editar materia"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteCourse.mutate(c.id)}
                        className="rounded border border-red-200 p-1.5 text-red-700 hover:bg-red-50"
                        aria-label="Eliminar materia"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  {c.description && <p className="text-xs text-[var(--text-secondary)]">{c.description}</p>}
                  <div className="flex flex-wrap gap-2 pt-1 text-xs">
                    <button
                      type="button"
                      onClick={() => onSelectCourse(c.id)}
                      className="font-semibold text-[var(--brand-primary)] underline"
                    >
                      {selected ? 'Editando módulos y nodos' : 'Gestionar módulos y nodos'}
                    </button>
                    <Link to={`/courses/${c.id}`} className="inline-flex items-center gap-1 text-[var(--text-secondary)] hover:underline">
                      Ver vista alumno <ExternalLink className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {editingCourse && (
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 space-y-2.5">
            <p className="text-xs font-bold text-amber-950">Editar materia: {editingCourse.title}</p>
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                value={editingCourse.title}
                onChange={(e) => setEditingCourse({ ...editingCourse, title: e.target.value })}
                className="rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-sm"
              />
              <input
                value={editingCourse.description ?? ''}
                onChange={(e) => setEditingCourse({ ...editingCourse, description: e.target.value })}
                placeholder="Descripción"
                className="rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-sm"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() =>
                  updateCourse.mutate({
                    id: editingCourse.id,
                    data: { title: editingCourse.title, description: editingCourse.description },
                  })
                }
                className="btn-primary px-3 py-1.5 text-xs font-semibold"
              >
                Guardar cambios
              </button>
              <button
                type="button"
                onClick={() => setEditingCourse(null)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Estructura de Módulos y Nodos del curso seleccionado */}
      {detailQuery.data && (
        <section className="surface-card p-5 space-y-4">
          <h3 className="text-base font-bold">Módulos y Nodos de: {detailQuery.data.title}</h3>

          <form onSubmit={createModule.mutate} className="grid gap-2 sm:grid-cols-3 rounded-xl bg-slate-50 p-3">
            <input
              required
              placeholder="Nuevo módulo (ej. Módulo 2: Práctica)"
              value={modTitle}
              onChange={(e) => setModTitle(e.target.value)}
              className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
            />
            <input
              placeholder="Descripción breve (opcional)"
              value={modDesc}
              onChange={(e) => setModDesc(e.target.value)}
              className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
            />
            <button type="submit" disabled={createModule.isPending} className="btn-primary px-4 py-2 text-xs font-semibold">
              <Plus className="inline h-3.5 w-3.5 mr-1" /> Agregar Módulo
            </button>
          </form>

          {detailQuery.data.modules.length > 0 && (
            <form onSubmit={createLesson.mutate} className="grid gap-2 sm:grid-cols-6 rounded-xl border border-[var(--border-subtle)] p-3">
              <select
                value={targetModuleId || detailQuery.data.modules[0].id}
                onChange={(e) => setTargetModuleId(e.target.value)}
                className="sm:col-span-2 rounded-lg border border-[var(--border-subtle)] bg-white px-2.5 py-2 text-xs"
              >
                {detailQuery.data.modules.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.title}
                  </option>
                ))}
              </select>
              <input
                required
                placeholder="Nombre del nodo / lección"
                value={lesTitle}
                onChange={(e) => setLesTitle(e.target.value)}
                className="sm:col-span-2 rounded-lg border border-[var(--border-subtle)] px-2.5 py-2 text-xs"
              />
              <select
                value={lesType}
                onChange={(e) => setLesType(e.target.value as LessonType)}
                className="rounded-lg border border-[var(--border-subtle)] bg-white px-2 py-2 text-xs"
              >
                <option value="micro_lesson">Microlección</option>
                <option value="study_guide_drill">Práctica de Guía</option>
                <option value="strong_exam">Prueba Fuerte</option>
              </select>
              <button type="submit" disabled={createLesson.isPending} className="btn-primary px-3 py-2 text-xs font-semibold">
                + Nodo
              </button>
              <div className="sm:col-span-6 flex flex-wrap items-center gap-4 text-xs text-[var(--text-secondary)]">
                <label className="flex items-center gap-1">
                  Minutos:
                  <input
                    type="number"
                    min={1}
                    max={120}
                    value={lesMinutes}
                    onChange={(e) => setLesMinutes(Number(e.target.value))}
                    className="w-14 rounded border px-1.5 py-0.5 text-xs"
                  />
                </label>
                <label className="flex items-center gap-1">
                  Nota mínima %:
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={lesPassPct}
                    onChange={(e) => setLesPassPct(Number(e.target.value))}
                    className="w-14 rounded border px-1.5 py-0.5 text-xs"
                  />
                </label>
                <label className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={lesCritical}
                    onChange={(e) => setLesCritical(e.target.checked)}
                  />
                  Protocolo crítico de seguridad
                </label>
                <label className="flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={lesRandomize}
                    onChange={(e) => setLesRandomize(e.target.checked)}
                  />
                  Aleatorizar preguntas por alumno
                </label>
                <label className="flex items-center gap-1">
                  Muestra N:
                  <input
                    type="number"
                    min={1}
                    max={50}
                    placeholder="Todas"
                    value={lesSampleSize}
                    onChange={(e) => setLesSampleSize(e.target.value)}
                    className="w-16 rounded border px-1.5 py-0.5 text-xs"
                  />
                </label>
              </div>
            </form>
          )}

          <div className="space-y-3">
            {detailQuery.data.modules.map((mod) => (
              <div key={mod.id} className="rounded-xl border border-[var(--border-subtle)] p-4 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-bold text-sm">{mod.title}</h4>
                    {mod.description && <p className="text-xs text-[var(--text-secondary)]">{mod.description}</p>}
                  </div>
                  <button
                    type="button"
                    onClick={() => deleteModule.mutate(mod.id)}
                    className="rounded border border-red-200 p-1.5 text-red-700 hover:bg-red-50"
                    aria-label="Eliminar módulo"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
                <div className="space-y-1.5">
                  {mod.lessons.map((les) => (
                    <div key={les.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs">
                      <div>
                        <span className="font-semibold">{les.title}</span>
                        <span className="ml-2 rounded bg-white px-2 py-0.5 text-[11px] font-medium border border-[var(--border-subtle)]">
                          {les.lesson_type === 'strong_exam'
                            ? 'Prueba Fuerte'
                            : les.lesson_type === 'study_guide_drill'
                              ? 'Repaso de Guía'
                              : 'Microlección'}
                        </span>
                        <span className="ml-2 text-[var(--text-secondary)]">
                          {les.estimated_minutes} min • Min {les.passing_score_pct ?? 70}%
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => onJumpToChallenges(activeCourseId, les.id)}
                          className="btn-primary px-2.5 py-1 text-[11px] font-semibold"
                        >
                          Retos / IA / Prueba
                        </button>
                        <button
                          type="button"
                          onClick={() => deleteLesson.mutate(les.id)}
                          className="rounded border border-red-200 p-1 text-red-700 hover:bg-red-50"
                          aria-label="Eliminar nodo"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
