import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BarChart3, Copy, QrCode, RefreshCw, Users } from 'lucide-react';
import { EmptyState, ErrorBanner, LoadingState, SuccessBanner } from '../ui/StatusStates';
import { apiRequest, getAccessToken, API_BASE } from '../../services/apiClient';
import type { AIJobOut, ClassroomAnalytics, ClassroomOut, CurriculumVersionOut, ProgramOut } from '../../types/api';
import { scopePrefix, type StudioScope } from './studioHelpers';

export function AnalyticsInvitesTab({ scope }: { scope: StudioScope }) {
  const queryClient = useQueryClient();
  const prefix = scopePrefix(scope);
  const [selectedClassroomId, setSelectedClassroomId] = useState('');
  const [newClassCode, setNewClassCode] = useState('');
  const [newClassName, setNewClassName] = useState('');
  const [qrSvg, setQrSvg] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const classroomsQuery = useQuery({
    queryKey: ['studio-classrooms', prefix],
    queryFn: () => apiRequest<ClassroomOut[]>(`/orgs/${(scope as { orgId: string }).orgId}/classrooms`),
    enabled: scope.mode === 'org',
  });

  const programsQuery = useQuery({
    queryKey: ['studio-programs-analytics', prefix],
    queryFn: () => apiRequest<ProgramOut[]>(`/orgs/${(scope as { orgId: string }).orgId}/programs`),
    enabled: scope.mode === 'org',
  });

  const firstProgId = programsQuery.data?.[0]?.id;
  const cvsQuery = useQuery({
    queryKey: ['studio-cvs-analytics', prefix, firstProgId],
    queryFn: () =>
      apiRequest<CurriculumVersionOut[]>(
        `/orgs/${(scope as { orgId: string }).orgId}/programs/${firstProgId}/curriculum-versions`
      ),
    enabled: scope.mode === 'org' && Boolean(firstProgId),
  });

  const activeClassroom =
    classroomsQuery.data?.find((c) => c.id === selectedClassroomId) || classroomsQuery.data?.[0] || null;

  const analyticsQuery = useQuery({
    queryKey: ['studio-classroom-analytics', prefix, activeClassroom?.id],
    queryFn: () =>
      apiRequest<ClassroomAnalytics>(
        `/orgs/${(scope as { orgId: string }).orgId}/analytics/classrooms/${activeClassroom!.id}`
      ),
    enabled: scope.mode === 'org' && Boolean(activeClassroom?.id),
  });

  const jobsQuery = useQuery({
    queryKey: ['studio-ai-jobs', prefix],
    queryFn: () => apiRequest<AIJobOut[]>(`${prefix}/ai/jobs`),
  });

  const publishedCvId = cvsQuery.data?.find((c) => c.status === 'published')?.id;

  const createClassroom = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      return apiRequest<ClassroomOut>(`/orgs/${(scope as { orgId: string }).orgId}/classrooms`, {
        method: 'POST',
        body: JSON.stringify({
          curriculum_version_id: publishedCvId,
          code: newClassCode,
          name: newClassName,
          energy_enabled: false,
        }),
      });
    },
    onSuccess: (created) => {
      setNewClassCode('');
      setNewClassName('');
      setSelectedClassroomId(created.id);
      setMsg(`Aula "${created.name}" creada con código de invitación ${created.invite_code}.`);
      void queryClient.invalidateQueries({ queryKey: ['studio-classrooms', prefix] });
    },
  });

  const rotateInvite = useMutation({
    mutationFn: (classroomId: string) =>
      apiRequest<ClassroomOut>(
        `/orgs/${(scope as { orgId: string }).orgId}/classrooms/${classroomId}/rotate-invite`,
        { method: 'POST' }
      ),
    onSuccess: (updated) => {
      setMsg(`Nuevo código generado: ${updated.invite_code}`);
      setQrSvg(null);
      void queryClient.invalidateQueries({ queryKey: ['studio-classrooms', prefix] });
    },
  });

  const loadQrSvg = async (classroomId: string) => {
    const token = getAccessToken();
    const res = await fetch(
      `${API_BASE}/orgs/${(scope as { orgId: string }).orgId}/classrooms/${classroomId}/invite-qr`,
      {
        credentials: 'include',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }
    );
    if (res.ok) {
      setQrSvg(await res.text());
    }
  };

  return (
    <div className="space-y-5">
      {msg && <SuccessBanner message={msg} />}
      {(createClassroom.error || rotateInvite.error) && (
        <ErrorBanner message={((createClassroom.error || rotateInvite.error) as Error).message} />
      )}

      {scope.mode === 'org' ? (
        <>
          <section className="surface-card p-5 space-y-4">
            <h2 className="flex items-center gap-2 text-base font-bold">
              <Users className="h-5 w-5 text-[var(--brand-primary)]" /> Aulas, Enlaces de Invitación y QR
            </h2>

            {publishedCvId && (
              <form onSubmit={createClassroom.mutate} className="grid gap-2 sm:grid-cols-3 rounded-xl bg-slate-50 p-3">
                <input
                  required
                  placeholder="Código aula (ej. FIS-2026-A)"
                  value={newClassCode}
                  onChange={(e) => setNewClassCode(e.target.value)}
                  className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-xs"
                />
                <input
                  required
                  placeholder="Nombre del aula o grupo"
                  value={newClassName}
                  onChange={(e) => setNewClassName(e.target.value)}
                  className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-xs"
                />
                <button type="submit" disabled={createClassroom.isPending} className="btn-primary px-4 py-2 text-xs font-semibold">
                  Crear Aula con Código
                </button>
              </form>
            )}

            {classroomsQuery.isLoading ? (
              <LoadingState label="Cargando aulas..." />
            ) : !classroomsQuery.data?.length ? (
              <EmptyState
                title="Aún no tienes aulas activas"
                description="Publica un pensum en la pestaña Guías, Temarios y Pensum para abrir tu primera cohorte con código QR."
              />
            ) : (
              <div className="space-y-3">
                <select
                  value={activeClassroom?.id || ''}
                  onChange={(e) => {
                    setSelectedClassroomId(e.target.value);
                    setQrSvg(null);
                  }}
                  className="w-full max-w-md rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm font-medium"
                >
                  {classroomsQuery.data.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.code}) — Invitación: {c.invite_code ?? 'Pendiente'}
                    </option>
                  ))}
                </select>

                {activeClassroom && (
                  <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-accent-soft)]/50 p-4 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="text-xs font-bold text-[var(--brand-primary)]">
                          Código para compartir con tus estudiantes:
                        </p>
                        <p className="text-lg font-extrabold tracking-wider">
                          {activeClassroom.invite_code || 'Sin código'}
                        </p>
                        {activeClassroom.invite_code && (
                          <p className="text-xs text-[var(--text-secondary)]">
                            Enlace directo: {window.location.origin}/unirse/{activeClassroom.invite_code}
                          </p>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {activeClassroom.invite_code && (
                          <button
                            type="button"
                            onClick={() => {
                              void navigator.clipboard?.writeText(
                                `${window.location.origin}/unirse/${activeClassroom.invite_code}`
                              );
                              setMsg('Enlace de invitación copiado al portapapeles.');
                            }}
                            className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-1.5 text-xs font-semibold"
                          >
                            <Copy className="h-3.5 w-3.5" /> Copiar Link
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => void loadQrSvg(activeClassroom.id)}
                          className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-1.5 text-xs font-semibold"
                        >
                          <QrCode className="h-3.5 w-3.5" /> Ver QR
                        </button>
                        <button
                          type="button"
                          onClick={() => rotateInvite.mutate(activeClassroom.id)}
                          className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-1.5 text-xs font-semibold"
                        >
                          <RefreshCw className="h-3.5 w-3.5" /> Rotar Código
                        </button>
                      </div>
                    </div>

                    {qrSvg && (
                      <div
                        className="inline-block rounded-xl border border-slate-200 bg-white p-3"
                        dangerouslySetInnerHTML={{ __html: qrSvg }}
                      />
                    )}
                  </div>
                )}
              </div>
            )}
          </section>

          {analyticsQuery.data && (
            <section className="surface-card p-5 space-y-4">
              <h3 className="flex items-center gap-2 text-base font-bold">
                <BarChart3 className="h-5 w-5 text-[var(--brand-primary)]" /> Analíticas de Desempeño ({analyticsQuery.data.classroom_name})
              </h3>
              <div className="grid gap-3 sm:grid-cols-4">
                <div className="rounded-xl bg-slate-50 p-3">
                  <p className="text-xs text-[var(--text-secondary)]">Estudiantes</p>
                  <p className="text-2xl font-extrabold">{analyticsQuery.data.enrolled_students}</p>
                </div>
                <div className="rounded-xl bg-slate-50 p-3">
                  <p className="text-xs text-[var(--text-secondary)]">Lecciones completadas</p>
                  <p className="text-2xl font-extrabold">{analyticsQuery.data.completed_lesson_records}</p>
                </div>
                <div className="rounded-xl bg-slate-50 p-3">
                  <p className="text-xs text-[var(--text-secondary)]">Nota promedio</p>
                  <p className="text-2xl font-extrabold">{analyticsQuery.data.avg_lesson_score_pct}%</p>
                </div>
                <div className="rounded-xl bg-slate-50 p-3">
                  <p className="text-xs text-[var(--text-secondary)]">Precisión</p>
                  <p className="text-2xl font-extrabold">{analyticsQuery.data.overall_accuracy_pct}%</p>
                </div>
              </div>
              {analyticsQuery.data.hardest_challenges.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-bold uppercase text-[var(--text-secondary)]">
                    Retos con mayor tasa de error (prioridad de repaso)
                  </p>
                  <ul className="space-y-1.5 text-xs">
                    {analyticsQuery.data.hardest_challenges.map((ch) => (
                      <li key={ch.challenge_id} className="flex items-center justify-between rounded bg-amber-50 px-3 py-2">
                        <span className="truncate pr-3 font-medium">{ch.prompt}</span>
                        <span className="shrink-0 font-bold text-amber-900">{ch.error_rate_pct}% error</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          )}
        </>
      ) : (
        <EmptyState
          title="Ámbito Catálogo Público Global"
          description="Las invitaciones por aula están disponibles al seleccionar una institución u organización específica."
        />
      )}

      <section className="surface-card p-5 space-y-2.5">
        <h3 className="text-sm font-bold uppercase text-[var(--text-secondary)]">Actividad Reciente del Asistente IA</h3>
        {!jobsQuery.data?.length ? (
          <p className="text-xs text-[var(--text-secondary)]">Aún no se han ejecutado tareas IA en este ámbito.</p>
        ) : (
          <ul className="space-y-1.5 text-xs">
            {jobsQuery.data.slice(0, 10).map((j) => (
              <li key={j.id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                <span>
                  <strong>{j.job_type}</strong> • {j.provider} ({j.status})
                </span>
                <span>{j.prompt_tokens + j.completion_tokens} tokens</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
