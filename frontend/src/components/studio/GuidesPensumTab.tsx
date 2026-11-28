import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BookMarked, CheckCircle2, Download, Edit3, Sparkles, Trash2 } from 'lucide-react';
import { EmptyState, ErrorBanner, LoadingState, SuccessBanner } from '../ui/StatusStates';
import { apiRequest, downloadAuthenticatedBlob } from '../../services/apiClient';
import type {
  CompetencyOut,
  CourseSummary,
  CurriculumVersionOut,
  GenerateStudyGuideResponse,
  GuideType,
  PedagogyStyle,
  ProgramOut,
  StudyGuideOut,
} from '../../types/api';
import { scopePrefix, type StudioScope } from './studioHelpers';

interface Props {
  scope: StudioScope;
  selectedCourseId: string;
}

export function GuidesPensumTab({ scope, selectedCourseId }: Props) {
  const queryClient = useQueryClient();
  const prefix = scopePrefix(scope);

  const [guideType, setGuideType] = useState<GuideType>('guia_estudio');
  const [title, setTitle] = useState('');
  const [markdown, setMarkdown] = useState('');
  const [pedagogyStyle, setPedagogyStyle] = useState<PedagogyStyle>('active_recall');
  const [aiNotes, setAiNotes] = useState('');
  const [editingGuide, setEditingGuide] = useState<StudyGuideOut | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  // Competencia y Programa (solo modo org)
  const [compCode, setCompCode] = useState('');
  const [compTitle, setCompTitle] = useState('');
  const [progCode, setProgCode] = useState('');
  const [progTitle, setProgTitle] = useState('');

  const coursesQuery = useQuery({
    queryKey: ['studio-courses', prefix],
    queryFn: () => apiRequest<CourseSummary[]>(`${prefix}/courses`),
  });

  const activeCourseId = selectedCourseId || coursesQuery.data?.[0]?.id || '';

  const guidesQuery = useQuery({
    queryKey: ['studio-guides', prefix, activeCourseId],
    queryFn: () =>
      apiRequest<StudyGuideOut[]>(
        `${prefix}/study-guides${activeCourseId ? `?course_id=${activeCourseId}` : ''}`
      ),
  });

  const competenciesQuery = useQuery({
    queryKey: ['studio-competencies', scope.mode === 'org' ? scope.orgId : 'none'],
    queryFn: () => apiRequest<CompetencyOut[]>(`/orgs/${(scope as { orgId: string }).orgId}/competencies`),
    enabled: scope.mode === 'org',
  });

  const programsQuery = useQuery({
    queryKey: ['studio-programs', scope.mode === 'org' ? scope.orgId : 'none'],
    queryFn: () => apiRequest<ProgramOut[]>(`/orgs/${(scope as { orgId: string }).orgId}/programs`),
    enabled: scope.mode === 'org',
  });

  const firstProgId = programsQuery.data?.[0]?.id;
  const cvsQuery = useQuery({
    queryKey: ['studio-cvs', scope.mode === 'org' ? scope.orgId : 'none', firstProgId],
    queryFn: () =>
      apiRequest<CurriculumVersionOut[]>(
        `/orgs/${(scope as { orgId: string }).orgId}/programs/${firstProgId}/curriculum-versions`
      ),
    enabled: scope.mode === 'org' && Boolean(firstProgId),
  });

  const createManualGuide = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      return apiRequest<StudyGuideOut>(`${prefix}/study-guides`, {
        method: 'POST',
        body: JSON.stringify({
          course_id: activeCourseId || null,
          guide_type: guideType,
          title,
          content_markdown: markdown,
          methodology_json: { pedagogical_approach: pedagogyStyle },
          status: 'draft',
        }),
      });
    },
    onSuccess: (g) => {
      setTitle('');
      setMarkdown('');
      setFeedback(`Guía "${g.title}" creada manualmente.`);
      void queryClient.invalidateQueries({ queryKey: ['studio-guides', prefix] });
    },
  });

  const generateAIGuide = useMutation({
    mutationFn: () =>
      apiRequest<GenerateStudyGuideResponse>(`${prefix}/ai/generate-study-guide`, {
        method: 'POST',
        body: JSON.stringify({
          course_id: activeCourseId || null,
          guide_type: guideType,
          topic: title || 'Guía de Estudio y Metodología',
          source_text: aiNotes,
          pedagogy_style: pedagogyStyle,
          save_as_draft: true,
        }),
      }),
    onSuccess: (res) => {
      setFeedback(`Guía "${res.title}" generada con IA (${res.provider}) y guardada en borrador.`);
      setAiNotes('');
      void queryClient.invalidateQueries({ queryKey: ['studio-guides', prefix] });
    },
  });

  const updateGuide = useMutation({
    mutationFn: (payload: { id: string; data: Partial<StudyGuideOut> }) =>
      apiRequest<StudyGuideOut>(`${prefix}/study-guides/${payload.id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload.data),
      }),
    onSuccess: (g) => {
      setEditingGuide(null);
      setFeedback(`Guía "${g.title}" actualizada (${g.status}).`);
      void queryClient.invalidateQueries({ queryKey: ['studio-guides', prefix] });
    },
  });

  const deleteGuide = useMutation({
    mutationFn: (id: string) => apiRequest<void>(`${prefix}/study-guides/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      setFeedback('Guía eliminada.');
      void queryClient.invalidateQueries({ queryKey: ['studio-guides', prefix] });
    },
  });

  const createCompetency = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      return apiRequest<CompetencyOut>(`/orgs/${(scope as { orgId: string }).orgId}/competencies`, {
        method: 'POST',
        body: JSON.stringify({ code: compCode, title: compTitle, education_level: 'specialized' }),
      });
    },
    onSuccess: () => {
      setCompCode('');
      setCompTitle('');
      setFeedback('Competencia agregada.');
      void queryClient.invalidateQueries({ queryKey: ['studio-competencies'] });
    },
  });

  const deleteCompetency = useMutation({
    mutationFn: (id: string) =>
      apiRequest<void>(`/orgs/${(scope as { orgId: string }).orgId}/competencies/${id}`, { method: 'DELETE' }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['studio-competencies'] }),
  });

  const createProgram = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      return apiRequest<ProgramOut>(`/orgs/${(scope as { orgId: string }).orgId}/programs`, {
        method: 'POST',
        body: JSON.stringify({ code: progCode, title: progTitle, education_level: 'specialized' }),
      });
    },
    onSuccess: () => {
      setProgCode('');
      setProgTitle('');
      setFeedback('Programa académico creado.');
      void queryClient.invalidateQueries({ queryKey: ['studio-programs'] });
    },
  });

  const err =
    createManualGuide.error || generateAIGuide.error || updateGuide.error || deleteGuide.error || createCompetency.error || createProgram.error;

  return (
    <div className="space-y-5">
      {feedback && <SuccessBanner message={feedback} />}
      {err && <ErrorBanner message={(err as Error).message} />}

      {/* Generación IA + Manual de Guías, Temarios y Metodología */}
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="surface-card p-5 space-y-3">
          <h2 className="flex items-center gap-2 text-base font-bold">
            <Sparkles className="h-5 w-5 text-[var(--brand-primary)]" /> Asistente IA: Redactar Guía, Temario o Metodología
          </h2>
          <div className="grid gap-2 sm:grid-cols-2">
            <select
              value={guideType}
              onChange={(e) => setGuideType(e.target.value as GuideType)}
              className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-xs font-semibold"
            >
              <option value="guia_estudio">Guía de Estudio</option>
              <option value="temario">Temario Detallado</option>
              <option value="metodologia">Metodología de Estudio</option>
              <option value="pensum">Pensum Narrativo</option>
              <option value="rubrica">Rúbrica de Evaluación</option>
            </select>
            <select
              value={pedagogyStyle}
              onChange={(e) => setPedagogyStyle(e.target.value as PedagogyStyle)}
              className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-xs font-semibold"
            >
              <option value="active_recall">Recuperación Activa</option>
              <option value="problem_based">Casos Prácticos</option>
              <option value="flipped_mastery">Aula Invertida</option>
              <option value="spaced_microlearning">Repaso Espaciado SM-2</option>
            </select>
          </div>
          <input
            placeholder="Título o tema de la guía..."
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
          />
          <textarea
            rows={4}
            placeholder="Pega tus apuntes o puntos clave para que la IA genere la guía profesional con plan de repaso..."
            value={aiNotes}
            onChange={(e) => setAiNotes(e.target.value)}
            className="w-full rounded-lg border border-[var(--border-subtle)] p-3 text-sm"
          />
          <button
            type="button"
            disabled={generateAIGuide.isPending || title.trim().length < 3}
            onClick={() => generateAIGuide.mutate()}
            className="btn-primary w-full py-2 text-xs font-semibold disabled:opacity-50"
          >
            {generateAIGuide.isPending ? 'Generando guía profesional...' : 'Generar Guía con IA'}
          </button>
        </section>

        <form onSubmit={createManualGuide.mutate} className="surface-card p-5 space-y-3">
          <h2 className="flex items-center gap-2 text-base font-bold">
            <BookMarked className="h-5 w-5 text-[var(--brand-primary)]" /> Crear Guía o Temario Manualmente
          </h2>
          <input
            required
            minLength={2}
            placeholder="Título de la guía / temario"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
          />
          <textarea
            required
            minLength={10}
            rows={6}
            placeholder="Escribe el contenido en texto o Markdown (# Unidad 1, objetivos, metodología, bibliografía...)"
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            className="w-full rounded-lg border border-[var(--border-subtle)] p-3 text-sm"
          />
          <button type="submit" disabled={createManualGuide.isPending} className="btn-primary w-full py-2 text-xs font-semibold">
            Guardar Guía Manual
          </button>
        </form>
      </div>

      {/* Lista CRUD de guías */}
      <section className="surface-card p-5 space-y-3">
        <h3 className="text-sm font-bold uppercase text-[var(--text-secondary)]">
          Guías, Temarios y Metodologías ({guidesQuery.data?.length ?? 0})
        </h3>
        {guidesQuery.isLoading ? (
          <LoadingState label="Cargando guías..." />
        ) : !guidesQuery.data?.length ? (
          <EmptyState title="Sin guías registradas" description="Crea manualmente o pide a la IA una guía profesional para tus alumnos." />
        ) : (
          <div className="space-y-2.5">
            {guidesQuery.data.map((g) => (
              <div key={g.id} className="rounded-xl border border-[var(--border-subtle)] bg-white p-4 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <span className="rounded bg-[var(--bg-accent-soft)] px-2 py-0.5 text-[11px] font-bold text-[var(--brand-primary)]">
                      {g.guide_type} {g.ai_generated ? '• IA' : '• Manual'}
                    </span>
                    <h4 className="mt-1 font-bold text-sm">{g.title}</h4>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() =>
                        void downloadAuthenticatedBlob(`${prefix}/study-guides/${g.id}/pdf`, `guia-${g.id}.pdf`)
                      }
                      className="rounded border border-[var(--border-subtle)] px-2.5 py-1 text-xs font-semibold hover:bg-slate-50"
                      title="Descargar PDF imprimible"
                    >
                      <Download className="inline h-3.5 w-3.5 mr-1" /> PDF
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        updateGuide.mutate({
                          id: g.id,
                          data: { status: g.status === 'published' ? 'draft' : 'published' },
                        })
                      }
                      className="rounded border border-[var(--border-subtle)] px-2.5 py-1 text-xs font-semibold hover:bg-slate-50"
                    >
                      <CheckCircle2 className="inline h-3.5 w-3.5 mr-1 text-emerald-600" />
                      {g.status === 'published' ? 'Publicada' : 'Publicar'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingGuide(g)}
                      className="rounded border border-[var(--border-subtle)] p-1.5 hover:bg-slate-50"
                      aria-label="Editar guía"
                    >
                      <Edit3 className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteGuide.mutate(g.id)}
                      className="rounded border border-red-200 p-1.5 text-red-700 hover:bg-red-50"
                      aria-label="Eliminar guía"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                <pre className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-[var(--text-secondary)] font-sans max-h-40 overflow-y-auto">
                  {g.content_markdown}
                </pre>
              </div>
            ))}
          </div>
        )}

        {editingGuide && (
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 space-y-2.5">
            <p className="text-xs font-bold text-amber-950">Editar guía: {editingGuide.title}</p>
            <input
              value={editingGuide.title}
              onChange={(e) => setEditingGuide({ ...editingGuide, title: e.target.value })}
              className="w-full rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-sm"
            />
            <textarea
              rows={5}
              value={editingGuide.content_markdown}
              onChange={(e) => setEditingGuide({ ...editingGuide, content_markdown: e.target.value })}
              className="w-full rounded-lg border border-amber-300 bg-white p-2.5 text-xs"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() =>
                  updateGuide.mutate({
                    id: editingGuide.id,
                    data: { title: editingGuide.title, content_markdown: editingGuide.content_markdown },
                  })
                }
                className="btn-primary px-3 py-1.5 text-xs font-semibold"
              >
                Guardar
              </button>
              <button
                type="button"
                onClick={() => setEditingGuide(null)}
                className="rounded border bg-white px-3 py-1.5 text-xs font-semibold"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Competencias y Programas/Pensum (ámbito org) */}
      {scope.mode === 'org' && (
        <div className="grid gap-5 lg:grid-cols-2">
          <section className="surface-card p-5 space-y-3">
            <h3 className="text-sm font-bold">Competencias Evaluables</h3>
            <form onSubmit={createCompetency.mutate} className="grid gap-2 sm:grid-cols-3">
              <input
                required
                placeholder="Código (BIO-01)"
                value={compCode}
                onChange={(e) => setCompCode(e.target.value)}
                className="rounded-lg border px-2.5 py-1.5 text-xs"
              />
              <input
                required
                placeholder="Título competencia"
                value={compTitle}
                onChange={(e) => setCompTitle(e.target.value)}
                className="rounded-lg border px-2.5 py-1.5 text-xs"
              />
              <button type="submit" className="btn-primary px-3 py-1.5 text-xs font-semibold">
                + Competencia
              </button>
            </form>
            <ul className="space-y-1.5 text-xs">
              {(competenciesQuery.data ?? []).map((comp) => (
                <li key={comp.id} className="flex items-center justify-between rounded bg-slate-50 px-3 py-1.5">
                  <span>
                    <strong>{comp.code}</strong> — {comp.title}
                  </span>
                  {comp.organization_id && (
                    <button
                      type="button"
                      onClick={() => deleteCompetency.mutate(comp.id)}
                      className="text-red-700 hover:underline"
                    >
                      Eliminar
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </section>

          <section className="surface-card p-5 space-y-3">
            <h3 className="text-sm font-bold">Programas y Pensums</h3>
            <form onSubmit={createProgram.mutate} className="grid gap-2 sm:grid-cols-3">
              <input
                required
                placeholder="Código (PROG-01)"
                value={progCode}
                onChange={(e) => setProgCode(e.target.value)}
                className="rounded-lg border px-2.5 py-1.5 text-xs"
              />
              <input
                required
                placeholder="Nombre del programa"
                value={progTitle}
                onChange={(e) => setProgTitle(e.target.value)}
                className="rounded-lg border px-2.5 py-1.5 text-xs"
              />
              <button type="submit" className="btn-primary px-3 py-1.5 text-xs font-semibold">
                + Programa
              </button>
            </form>
            <ul className="space-y-1.5 text-xs">
              {(programsQuery.data ?? []).map((p) => (
                <li key={p.id} className="rounded bg-slate-50 px-3 py-2">
                  <strong>{p.code}</strong> — {p.title}
                </li>
              ))}
              {(cvsQuery.data ?? []).map((cv) => (
                <li key={cv.id} className="rounded border border-slate-200 px-3 py-1.5">
                  Pensum v{cv.version_number}: {cv.title} ({cv.status})
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
