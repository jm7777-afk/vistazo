import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { EmptyState, ErrorBanner, LoadingState, SuccessBanner } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type {
  AIJobOut,
  AIProviderConfigOut,
  AuditLogOut,
  CertificateOut,
  ChallengeAuthorOut,
  ClassroomAnalytics,
  ClassroomOut,
  ClassroomStudentOut,
  CourseDetail,
  CourseSummary,
  GenerateLessonDraftResponse,
  LessonVersionOut,
  OrgAnalyticsOverview,
  UIProfile,
} from '../types/api';

export function InstructorPage() {
  const { activeOrg } = useAppState();
  const [selectedClassroomId, setSelectedClassroomId] = useState<string>('');

  const classroomsQuery = useQuery({
    queryKey: ['instructor-classrooms', activeOrg?.organization_id],
    queryFn: () => apiRequest<ClassroomOut[]>(`/orgs/${activeOrg!.organization_id}/classrooms`),
    enabled: Boolean(activeOrg),
  });

  const activeClassroomId = selectedClassroomId || classroomsQuery.data?.[0]?.id || '';

  const studentsQuery = useQuery({
    queryKey: ['classroom-students', activeOrg?.organization_id, activeClassroomId],
    queryFn: () =>
      apiRequest<ClassroomStudentOut[]>(`/orgs/${activeOrg!.organization_id}/classrooms/${activeClassroomId}/students`),
    enabled: Boolean(activeOrg && activeClassroomId),
  });

  const analyticsQuery = useQuery({
    queryKey: ['classroom-analytics', activeOrg?.organization_id, activeClassroomId],
    queryFn: () =>
      apiRequest<ClassroomAnalytics>(`/orgs/${activeOrg!.organization_id}/analytics/classrooms/${activeClassroomId}`),
    enabled: Boolean(activeOrg && activeClassroomId),
  });

  if (!activeOrg) {
    return <EmptyState title="Selecciona una organización" description="El panel de instructor requiere contexto institucional." />;
  }

  return (
    <div className="space-y-6">
      <div className="surface-card p-6">
        <h1 className="text-xl font-bold">Panel de Instructor — {activeOrg.organization_name}</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Solo ves las aulas y estudiantes explícitamente asignados a tu cuenta.
        </p>
      </div>

      {analyticsQuery.data && (
        <div className="grid gap-3 sm:grid-cols-4">
          <div className="surface-card p-4">
            <p className="text-xs text-[var(--text-secondary)]">Matriculados</p>
            <p className="text-2xl font-extrabold">{analyticsQuery.data.enrolled_students}</p>
          </div>
          <div className="surface-card p-4">
            <p className="text-xs text-[var(--text-secondary)]">Lecciones completadas</p>
            <p className="text-2xl font-extrabold">{analyticsQuery.data.completed_lesson_records}</p>
          </div>
          <div className="surface-card p-4">
            <p className="text-xs text-[var(--text-secondary)]">Nota promedio</p>
            <p className="text-2xl font-extrabold">{analyticsQuery.data.avg_lesson_score_pct}%</p>
          </div>
          <div className="surface-card p-4">
            <p className="text-xs text-[var(--text-secondary)]">Precisión global</p>
            <p className="text-2xl font-extrabold">{analyticsQuery.data.overall_accuracy_pct}%</p>
          </div>
        </div>
      )}

      {analyticsQuery.data && analyticsQuery.data.hardest_challenges.length > 0 && (
        <div className="surface-card p-5">
          <h2 className="text-base font-bold">Retos con mayor necesidad de refuerzo</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {analyticsQuery.data.hardest_challenges.map((ch) => (
              <li key={ch.challenge_id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                <span className="truncate pr-3">{ch.prompt}</span>
                <span className="shrink-0 font-semibold text-amber-800">{ch.error_rate_pct}% error</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {classroomsQuery.isLoading ? (
        <LoadingState label="Cargando aulas asignadas..." />
      ) : classroomsQuery.error ? (
        <ErrorBanner message={(classroomsQuery.error as Error).message} />
      ) : !classroomsQuery.data?.length ? (
        <EmptyState title="Sin aulas asignadas" description="Un coordinador debe asignarte a una cohorte." />
      ) : (
        <div className="surface-card p-5 space-y-4">
          <label className="block text-sm font-semibold">
            Aula asignada
            <select
              value={activeClassroomId}
              onChange={(e) => setSelectedClassroomId(e.target.value)}
              className="mt-1 w-full max-w-md rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
            >
              {classroomsQuery.data.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.code})
                </option>
              ))}
            </select>
          </label>

          {studentsQuery.isLoading ? (
            <LoadingState label="Cargando estudiantes..." />
          ) : studentsQuery.error ? (
            <ErrorBanner message={(studentsQuery.error as Error).message} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] text-xs text-[var(--text-secondary)]">
                    <th className="py-2 pr-4">Estudiante</th>
                    <th className="py-2 pr-4">Estado</th>
                    <th className="py-2 pr-4">Lecciones completadas</th>
                    <th className="py-2">Promedio</th>
                  </tr>
                </thead>
                <tbody>
                  {(studentsQuery.data ?? []).map((st) => (
                    <tr key={st.user_id} className="border-b border-slate-100">
                      <td className="py-2.5 pr-4 font-medium">{st.full_name}</td>
                      <td className="py-2.5 pr-4">{st.enrollment_status}</td>
                      <td className="py-2.5 pr-4">{st.completed_lessons}</td>
                      <td className="py-2.5 font-semibold">{st.avg_score_pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <InstructorAIGenerator orgId={activeOrg.organization_id} />
    </div>
  );
}

function InstructorAIGenerator({ orgId }: { orgId: string }) {
  const queryClient = useQueryClient();
  const [sourceText, setSourceText] = useState('');
  const [selectedLessonId, setSelectedLessonId] = useState('');
  const [draftResult, setDraftResult] = useState<GenerateLessonDraftResponse | null>(null);

  const coursesQuery = useQuery({
    queryKey: ['org-courses-ai', orgId],
    queryFn: () => apiRequest<CourseSummary[]>(`/orgs/${orgId}/courses`),
  });

  const firstCourseId = coursesQuery.data?.[0]?.id;
  const courseDetailQuery = useQuery({
    queryKey: ['course-detail-ai', firstCourseId],
    queryFn: () => apiRequest<CourseDetail>(`/courses/${firstCourseId}`),
    enabled: Boolean(firstCourseId),
  });

  const jobsQuery = useQuery({
    queryKey: ['org-ai-jobs', orgId],
    queryFn: () => apiRequest<AIJobOut[]>(`/orgs/${orgId}/ai/jobs`),
  });

  const lessons = (courseDetailQuery.data?.modules ?? []).flatMap((m) => m.lessons);
  const targetLessonId = selectedLessonId || lessons[0]?.id || '';

  const versionsQuery = useQuery({
    queryKey: ['lesson-versions-author', orgId, targetLessonId],
    queryFn: () => apiRequest<LessonVersionOut[]>(`/orgs/${orgId}/lessons/${targetLessonId}/versions`),
    enabled: Boolean(targetLessonId),
  });

  const draftVersion = versionsQuery.data?.find((v) => v.status === 'draft');

  const draftChallengesQuery = useQuery({
    queryKey: ['draft-challenges-author', orgId, draftVersion?.id],
    queryFn: () =>
      apiRequest<ChallengeAuthorOut[]>(`/orgs/${orgId}/lesson-versions/${draftVersion!.id}/challenges`),
    enabled: Boolean(draftVersion?.id),
  });

  const publishVersionMutation = useMutation({
    mutationFn: (lvId: string) =>
      apiRequest<LessonVersionOut>(`/orgs/${orgId}/lesson-versions/${lvId}/publish`, { method: 'POST' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['lesson-versions-author', orgId, targetLessonId] });
      void queryClient.invalidateQueries({ queryKey: ['course-detail-ai', firstCourseId] });
    },
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      const lv = await apiRequest<{ id: string }>(`/orgs/${orgId}/lessons/${targetLessonId}/versions`, {
        method: 'POST',
        body: JSON.stringify({ summary: 'Borrador generado con IA', requires_revalidation: false }),
      });
      return apiRequest<GenerateLessonDraftResponse>(`/orgs/${orgId}/ai/generate-lesson-draft`, {
        method: 'POST',
        body: JSON.stringify({ lesson_version_id: lv.id, source_text: sourceText }),
      });
    },
    onSuccess: (res) => {
      setDraftResult(res);
      setSourceText('');
      void queryClient.invalidateQueries({ queryKey: ['org-ai-jobs', orgId] });
      void queryClient.invalidateQueries({ queryKey: ['lesson-versions-author', orgId, targetLessonId] });
    },
  });

  return (
    <section className="surface-card p-5 space-y-4">
      <div>
        <h2 className="text-base font-bold">Generador IA de Borradores de Lección</h2>
        <p className="text-xs text-[var(--text-secondary)]">
          Pega texto autorizado del manual; se crean 5–8 retos en estado borrador para tu revisión humana.
        </p>
      </div>

      {draftResult && (
        <SuccessBanner
          message={`Borrador generado (${draftResult.challenges_created} retos en estado draft vía ${draftResult.provider}).`}
        />
      )}
      {generateMutation.error && <ErrorBanner message={(generateMutation.error as Error).message} />}

      {lessons.length > 0 && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            generateMutation.mutate();
          }}
          className="space-y-3"
        >
          <select
            value={targetLessonId}
            onChange={(e) => setSelectedLessonId(e.target.value)}
            className="w-full max-w-md rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
          >
            {lessons.map((l) => (
              <option key={l.id} value={l.id}>
                Lección base: {l.title}
              </option>
            ))}
          </select>
          <textarea
            required
            minLength={80}
            rows={4}
            placeholder="Pega al menos 80 caracteres del protocolo o tema a convertir en retos..."
            value={sourceText}
            onChange={(e) => setSourceText(e.target.value)}
            className="w-full rounded-lg border border-[var(--border-subtle)] p-3 text-sm"
          />
          <button
            type="submit"
            disabled={generateMutation.isPending}
            className="btn-primary px-4 py-2 text-xs font-semibold"
          >
            {generateMutation.isPending ? 'Generando borrador...' : 'Generar borrador IA (5–8 retos)'}
          </button>
        </form>
      )}

      {draftVersion && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 space-y-2.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-xs font-bold text-amber-950">
                Borrador pendiente: Versión v{draftVersion.version_number}
              </p>
              <p className="text-xs text-amber-800">{draftVersion.summary}</p>
            </div>
            <button
              type="button"
              disabled={publishVersionMutation.isPending || !(draftChallengesQuery.data?.length)}
              onClick={() => publishVersionMutation.mutate(draftVersion.id)}
              className="btn-primary px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
            >
              {publishVersionMutation.isPending ? 'Publicando...' : 'Aprobar y publicar versión'}
            </button>
          </div>
          {draftChallengesQuery.data && draftChallengesQuery.data.length > 0 && (
            <ul className="space-y-1 text-xs text-amber-950">
              {draftChallengesQuery.data.map((ch) => (
                <li key={ch.id} className="rounded bg-white/80 px-2.5 py-1.5">
                  <strong>[{ch.challenge_type}]</strong> {ch.prompt}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {jobsQuery.data && jobsQuery.data.length > 0 && (
        <div className="pt-2">
          <h3 className="text-xs font-bold uppercase text-[var(--text-secondary)]">Historial reciente de uso IA</h3>
          <ul className="mt-2 space-y-1 text-xs">
            {jobsQuery.data.slice(0, 5).map((j) => (
              <li key={j.id} className="flex justify-between rounded bg-slate-50 px-2.5 py-1.5">
                <span>
                  {j.job_type} ({j.provider}) — {j.status}
                </span>
                <span>{j.prompt_tokens + j.completion_tokens} tokens</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export function CoordinatorPage() {
  const { activeOrg } = useAppState();
  const queryClient = useQueryClient();
  const [progCode, setProgCode] = useState('');
  const [progTitle, setProgTitle] = useState('');
  const [okMsg, setOkMsg] = useState<string | null>(null);

  const programsQuery = useQuery({
    queryKey: ['org-programs', activeOrg?.organization_id],
    queryFn: () =>
      apiRequest<{ id: string; code: string; title: string; education_level: string }[]>(
        `/orgs/${activeOrg!.organization_id}/programs`
      ),
    enabled: Boolean(activeOrg),
  });

  const createProgram = useMutation({
    mutationFn: () =>
      apiRequest(`/orgs/${activeOrg!.organization_id}/programs`, {
        method: 'POST',
        body: JSON.stringify({ code: progCode, title: progTitle, education_level: 'rescue' }),
      }),
    onSuccess: () => {
      setProgCode('');
      setProgTitle('');
      setOkMsg('Programa formativo creado en tu organización.');
      void queryClient.invalidateQueries({ queryKey: ['org-programs', activeOrg?.organization_id] });
    },
  });

  if (!activeOrg) {
    return <EmptyState title="Selecciona una organización" description="Debes operar dentro de tu organización." />;
  }

  return (
    <div className="space-y-6">
      <div className="surface-card p-6">
        <h1 className="text-xl font-bold">Coordinación — {activeOrg.organization_name}</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Gestión aislada de programas, pensums y aulas.</p>
      </div>

      {okMsg && <SuccessBanner message={okMsg} />}
      {createProgram.error && <ErrorBanner message={(createProgram.error as Error).message} />}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          createProgram.mutate();
        }}
        className="surface-card grid gap-3 p-5 sm:grid-cols-3"
      >
        <input
          required
          placeholder="Código (ej. PROG-RES-02)"
          value={progCode}
          onChange={(e) => setProgCode(e.target.value)}
          className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
        />
        <input
          required
          placeholder="Nombre del programa"
          value={progTitle}
          onChange={(e) => setProgTitle(e.target.value)}
          className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
        />
        <button type="submit" disabled={createProgram.isPending} className="btn-primary px-4 py-2 text-sm font-semibold">
          Crear programa
        </button>
      </form>

      {programsQuery.isLoading ? (
        <LoadingState />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {(programsQuery.data ?? []).map((p) => (
            <div key={p.id} className="surface-card p-4">
              <span className="text-xs font-bold text-[var(--brand-primary)]">{p.code}</span>
              <h3 className="font-bold text-base">{p.title}</h3>
            </div>
          ))}
        </div>
      )}

      <CoordinatorOverviewPanel orgId={activeOrg.organization_id} />
      <CoordinatorClassroomsPanel orgId={activeOrg.organization_id} programId={programsQuery.data?.[0]?.id} />
      <CoordinatorCertificatesPanel orgId={activeOrg.organization_id} programId={programsQuery.data?.[0]?.id} />
      <AuditLogsPanel endpoint={`/orgs/${activeOrg.organization_id}/audit-logs`} title="Auditoría de la Organización" />
    </div>
  );
}

function CoordinatorClassroomsPanel({ orgId, programId }: { orgId: string; programId?: string }) {
  const queryClient = useQueryClient();
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [enrollEmail, setEnrollEmail] = useState('');
  const [selectedClassroom, setSelectedClassroom] = useState('');
  const [msg, setMsg] = useState<string | null>(null);

  const cvsQuery = useQuery({
    queryKey: ['org-cvs-manage', orgId, programId],
    queryFn: () =>
      apiRequest<{ id: string; title: string; status: string }[]>(
        `/orgs/${orgId}/programs/${programId}/curriculum-versions`
      ),
    enabled: Boolean(programId),
  });
  const classroomsQuery = useQuery({
    queryKey: ['coord-classrooms', orgId],
    queryFn: () => apiRequest<ClassroomOut[]>(`/orgs/${orgId}/classrooms`),
  });

  const publishedCvId = cvsQuery.data?.find((c) => c.status === 'published')?.id ?? '';
  const targetClassroom = selectedClassroom || classroomsQuery.data?.[0]?.id || '';

  const createClassroom = useMutation({
    mutationFn: () =>
      apiRequest<ClassroomOut>(`/orgs/${orgId}/classrooms`, {
        method: 'POST',
        body: JSON.stringify({
          curriculum_version_id: publishedCvId,
          code,
          name,
          energy_enabled: false,
        }),
      }),
    onSuccess: () => {
      setCode('');
      setName('');
      setMsg('Aula creada correctamente.');
      void queryClient.invalidateQueries({ queryKey: ['coord-classrooms', orgId] });
    },
  });

  const enrollStudent = useMutation({
    mutationFn: () =>
      apiRequest<{ status: string }>(`/orgs/${orgId}/classrooms/${targetClassroom}/enroll`, {
        method: 'POST',
        body: JSON.stringify({ student_email: enrollEmail }),
      }),
    onSuccess: () => {
      setEnrollEmail('');
      setMsg('Estudiante matriculado en el aula.');
    },
  });

  return (
    <section className="surface-card p-5 space-y-4">
      <h2 className="text-base font-bold">Gestión de Aulas y Matrículas</h2>
      {msg && <SuccessBanner message={msg} />}
      {(createClassroom.error || enrollStudent.error) && (
        <ErrorBanner message={((createClassroom.error || enrollStudent.error) as Error).message} />
      )}
      {publishedCvId && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createClassroom.mutate();
          }}
          className="grid gap-3 sm:grid-cols-3"
        >
          <input
            required
            placeholder="Código aula (ej. COH-2026-B)"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
          />
          <input
            required
            placeholder="Nombre del aula"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
          />
          <button type="submit" disabled={createClassroom.isPending} className="btn-primary px-4 py-2 text-xs font-semibold">
            Crear aula
          </button>
        </form>
      )}
      {classroomsQuery.data && classroomsQuery.data.length > 0 && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            enrollStudent.mutate();
          }}
          className="grid gap-3 sm:grid-cols-3"
        >
          <select
            value={targetClassroom}
            onChange={(e) => setSelectedClassroom(e.target.value)}
            className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
          >
            {classroomsQuery.data.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.code})
              </option>
            ))}
          </select>
          <input
            type="email"
            required
            placeholder="correo@estudiante.org"
            value={enrollEmail}
            onChange={(e) => setEnrollEmail(e.target.value)}
            className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
          />
          <button type="submit" disabled={enrollStudent.isPending} className="btn-primary px-4 py-2 text-xs font-semibold">
            Matricular estudiante
          </button>
        </form>
      )}
    </section>
  );
}

function AuditLogsPanel({ endpoint, title }: { endpoint: string; title: string }) {
  const logsQuery = useQuery({
    queryKey: ['audit-logs', endpoint],
    queryFn: () => apiRequest<AuditLogOut[]>(endpoint),
  });

  return (
    <section className="surface-card p-5 space-y-3">
      <h2 className="text-base font-bold">{title}</h2>
      {logsQuery.isLoading ? (
        <LoadingState label="Cargando bitácora..." />
      ) : !logsQuery.data?.length ? (
        <p className="text-xs text-[var(--text-secondary)]">Sin eventos registrados aún.</p>
      ) : (
        <ul className="space-y-1.5 text-xs">
          {logsQuery.data.slice(0, 12).map((log) => (
            <li key={log.id} className="flex flex-wrap items-center justify-between gap-2 rounded bg-slate-50 px-3 py-2">
              <span>
                <strong>{log.action}</strong> • {log.resource_type}
              </span>
              <span
                className={`rounded px-2 py-0.5 font-semibold ${
                  log.outcome === 'denied' ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'
                }`}
              >
                {log.outcome}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function CoordinatorOverviewPanel({ orgId }: { orgId: string }) {
  const overviewQuery = useQuery({
    queryKey: ['org-analytics-overview', orgId],
    queryFn: () => apiRequest<OrgAnalyticsOverview>(`/orgs/${orgId}/analytics/overview`),
  });

  if (overviewQuery.isLoading) return <LoadingState label="Cargando comparativa multi-cohorte..." />;
  if (!overviewQuery.data) return null;
  const ov = overviewQuery.data;

  return (
    <section className="surface-card p-5 space-y-4">
      <h2 className="text-base font-bold">Analíticas Multi-Cohorte</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="text-xs text-[var(--text-secondary)]">Aulas activas</p>
          <p className="text-xl font-extrabold">{ov.total_classrooms}</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="text-xs text-[var(--text-secondary)]">Estudiantes</p>
          <p className="text-xl font-extrabold">{ov.total_enrolled_students}</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="text-xs text-[var(--text-secondary)]">Certificados emitidos</p>
          <p className="text-xl font-extrabold">{ov.issued_certificates}</p>
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="text-xs text-[var(--text-secondary)]">Jobs IA</p>
          <p className="text-xl font-extrabold">{ov.ai_jobs_count}</p>
        </div>
      </div>
      {ov.cohorts.length > 0 && (
        <ul className="space-y-2 text-xs">
          {ov.cohorts.map((c) => (
            <li key={c.classroom_id} className="flex justify-between rounded-lg bg-slate-50 px-3 py-2">
              <span className="font-semibold">
                {c.classroom_name} ({c.classroom_code})
              </span>
              <span>
                {c.enrolled_students} alumnos • {c.completed_lessons} lecciones • {c.avg_score_pct}%
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function CoordinatorCertificatesPanel({ orgId, programId }: { orgId: string; programId?: string }) {
  const queryClient = useQueryClient();
  const [studentEmail, setStudentEmail] = useState('');
  const [signerTitle, setSignerTitle] = useState('Coordinación Académica');

  const cvsQuery = useQuery({
    queryKey: ['org-cvs-cert', orgId, programId],
    queryFn: () => apiRequest<{ id: string; title: string; status: string }[]>(`/orgs/${orgId}/programs/${programId}/curriculum-versions`),
    enabled: Boolean(programId),
  });

  const certsQuery = useQuery({
    queryKey: ['org-certs', orgId],
    queryFn: () => apiRequest<CertificateOut[]>(`/orgs/${orgId}/certificates`),
  });

  const publishedCvId = cvsQuery.data?.find((c) => c.status === 'published')?.id ?? '';

  const issueMutation = useMutation({
    mutationFn: () =>
      apiRequest<CertificateOut>(`/orgs/${orgId}/certificates/issue`, {
        method: 'POST',
        body: JSON.stringify({
          student_email: studentEmail,
          curriculum_version_id: publishedCvId,
          signer_title: signerTitle,
        }),
      }),
    onSuccess: () => {
      setStudentEmail('');
      void queryClient.invalidateQueries({ queryKey: ['org-certs', orgId] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (certId: string) =>
      apiRequest<CertificateOut>(`/orgs/${orgId}/certificates/${certId}/revoke`, {
        method: 'POST',
        body: JSON.stringify({ reason: 'Revocación administrativa institucional' }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['org-certs', orgId] });
    },
  });

  return (
    <section className="surface-card p-5 space-y-4">
      <h2 className="text-base font-bold">Emisión y Revocación de Certificados</h2>
      {issueMutation.error && <ErrorBanner message={(issueMutation.error as Error).message} />}

      {publishedCvId && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            issueMutation.mutate();
          }}
          className="grid gap-3 sm:grid-cols-3"
        >
          <input
            type="email"
            required
            placeholder="correo@estudiante.org"
            value={studentEmail}
            onChange={(e) => setStudentEmail(e.target.value)}
            className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
          />
          <input
            type="text"
            required
            value={signerTitle}
            onChange={(e) => setSignerTitle(e.target.value)}
            className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
          />
          <button type="submit" disabled={issueMutation.isPending} className="btn-primary px-4 py-2 text-xs font-semibold">
            Emitir certificado
          </button>
        </form>
      )}

      {certsQuery.data && certsQuery.data.length > 0 && (
        <ul className="space-y-2 text-xs">
          {certsQuery.data.map((c) => (
            <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 p-3">
              <span>
                <strong>{c.certificate_number}</strong> • {c.final_grade}% • {c.status}
              </span>
              {c.status !== 'revoked' && (
                <button
                  type="button"
                  onClick={() => revokeMutation.mutate(c.id)}
                  className="rounded border border-red-300 px-2.5 py-1 font-semibold text-red-700 hover:bg-red-50"
                >
                  Revocar
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function SuperAdminPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [sector, setSector] = useState('rescue_brigade');
  const [uiProfile, setUiProfile] = useState<UIProfile>('pro');
  const [coordEmail, setCoordEmail] = useState('');
  const [coordName, setCoordName] = useState('');
  const [progCode, setProgCode] = useState('');
  const [progTitle, setProgTitle] = useState('');

  const orgsQuery = useQuery({
    queryKey: ['admin-orgs'],
    queryFn: () =>
      apiRequest<{ id: string; name: string; slug: string; sector_type: string; default_ui_profile: string }[]>(
        '/admin/organizations'
      ),
  });

  const onboardOrg = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      return apiRequest('/admin/organizations/onboard', {
        method: 'POST',
        body: JSON.stringify({
          name,
          slug,
          sector_type: sector,
          default_ui_profile: uiProfile,
          coordinator_email: coordEmail,
          coordinator_name: coordName,
          initial_program_code: progCode,
          initial_program_title: progTitle,
        }),
      });
    },
    onSuccess: () => {
      setName('');
      setSlug('');
      setCoordEmail('');
      setCoordName('');
      setProgCode('');
      setProgTitle('');
      void queryClient.invalidateQueries({ queryKey: ['admin-orgs'] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="surface-card p-6">
        <h1 className="text-xl font-bold">Panel SuperAdministrador</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Onboarding atómico multi-institucional y proveedores IA.</p>
      </div>

      {onboardOrg.error && <ErrorBanner message={(onboardOrg.error as Error).message} />}
      {onboardOrg.isSuccess && <SuccessBanner message="Institución y coordinador creados correctamente." />}

      <form onSubmit={onboardOrg.mutate} className="surface-card grid gap-3 p-5 sm:grid-cols-2">
        <input
          required
          placeholder="Nombre institución"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
        />
        <input
          required
          placeholder="slug-institucion"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
        />
        <select
          value={sector}
          onChange={(e) => setSector(e.target.value)}
          className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
        >
          <option value="rescue_brigade">Brigada de Rescate</option>
          <option value="primary_school">Educación Primaria</option>
          <option value="secondary_school">Educación Secundaria</option>
          <option value="high_school">Bachillerato</option>
          <option value="university">Universidad</option>
          <option value="technical_academy">Academia Técnica</option>
          <option value="specialized_training">Formación Especializada</option>
        </select>
        <select
          value={uiProfile}
          onChange={(e) => setUiProfile(e.target.value as UIProfile)}
          className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
        >
          <option value="pro">Perfil Pro / Rescate</option>
          <option value="youth">Perfil Juvenil</option>
          <option value="kids">Perfil Infantil</option>
        </select>
        <input
          required
          placeholder="Nombre del coordinador"
          value={coordName}
          onChange={(e) => setCoordName(e.target.value)}
          className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
        />
        <input
          required
          type="email"
          placeholder="correo@coordinador.org"
          value={coordEmail}
          onChange={(e) => setCoordEmail(e.target.value)}
          className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
        />
        <input
          required
          placeholder="Código programa inicial"
          value={progCode}
          onChange={(e) => setProgCode(e.target.value)}
          className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
        />
        <input
          required
          placeholder="Título programa inicial"
          value={progTitle}
          onChange={(e) => setProgTitle(e.target.value)}
          className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
        />
        <button type="submit" disabled={onboardOrg.isPending} className="btn-primary sm:col-span-2 px-4 py-2 text-sm font-semibold">
          Ejecutar onboarding institucional
        </button>
      </form>

      {orgsQuery.isLoading ? (
        <LoadingState />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {(orgsQuery.data ?? []).map((o) => (
            <div key={o.id} className="surface-card p-4">
              <h3 className="font-bold">{o.name}</h3>
              <p className="text-xs text-[var(--text-secondary)]">
                {o.slug} • {o.sector_type} • UI {o.default_ui_profile}
              </p>
            </div>
          ))}
        </div>
      )}

      <AdminAIProvidersPanel />
      <AuditLogsPanel endpoint="/admin/audit-logs" title="Auditoría Global de Plataforma" />
    </div>
  );
}

function AdminAIProvidersPanel() {
  const queryClient = useQueryClient();
  const providersQuery = useQuery({
    queryKey: ['admin-ai-providers'],
    queryFn: () => apiRequest<AIProviderConfigOut[]>('/admin/ai/providers'),
  });

  const switchMutation = useMutation({
    mutationFn: (p: AIProviderConfigOut) =>
      apiRequest<AIProviderConfigOut>('/admin/ai/providers', {
        method: 'PUT',
        body: JSON.stringify({
          provider: p.provider,
          model_name: p.model_name,
          max_tokens: p.max_tokens,
          daily_org_job_limit: p.daily_org_job_limit,
        }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin-ai-providers'] });
    },
  });

  return (
    <section className="surface-card p-5 space-y-3">
      <h2 className="text-base font-bold">Proveedores IA Pedagógica</h2>
      <p className="text-xs text-[var(--text-secondary)]">
        Cambia el proveedor activo sin reiniciar; si no hay API key, conmuta automáticamente al fallback seguro.
      </p>
      {providersQuery.isLoading ? (
        <LoadingState />
      ) : (
        <div className="grid gap-3 sm:grid-cols-3">
          {(providersQuery.data ?? []).map((p) => (
            <div key={p.id} className="rounded-xl border border-[var(--border-subtle)] p-4">
              <p className="font-bold text-sm uppercase">{p.provider}</p>
              <p className="text-xs text-[var(--text-secondary)]">{p.model_name}</p>
              <p className="mt-1 text-[11px]">
                API Key: {p.has_api_key_configured ? 'Configurada' : 'Sin clave (usará fallback)'}
              </p>
              <button
                type="button"
                disabled={p.is_active || switchMutation.isPending}
                onClick={() => switchMutation.mutate(p)}
                className="btn-primary mt-3 w-full py-1.5 text-xs font-semibold disabled:opacity-50"
              >
                {p.is_active ? 'Activo' : 'Activar'}
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function ProfilePage() {
  const { user, uiProfile, setUiProfile, logout } = useAppState();
  const [confirmAnon, setConfirmAnon] = useState(false);
  if (!user) return null;

  const profiles: { id: UIProfile; label: string; desc: string }[] = [
    { id: 'kids', label: 'Infantil y Primaria', desc: 'Mayor espaciado táctil y tonos cálidos.' },
    { id: 'youth', label: 'Juvenil y Secundaria', desc: 'Contraste vibrante para micro-retos dinámicos.' },
    { id: 'pro', label: 'Profesional / Universitario / Rescate', desc: 'Sobrio, técnico y de máxima legibilidad operativa.' },
  ];

  const handleAnonymize = async () => {
    await apiRequest<void>('/auth/me/anonymize', { method: 'POST' }, false);
    await logout();
  };

  return (
    <div className="mx-auto max-w-xl space-y-5">
      <div className="surface-card p-6">
        <h1 className="text-xl font-bold">{user.full_name}</h1>
        <p className="text-sm text-[var(--text-secondary)]">{user.email}</p>
      </div>
      <div className="surface-card p-6 space-y-3">
        <h2 className="font-bold text-base">Adaptación visual por perfil</h2>
        {profiles.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => setUiProfile(p.id)}
            className={`w-full rounded-xl border p-4 text-left ${
              uiProfile === p.id
                ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)]'
                : 'border-[var(--border-subtle)] bg-white'
            }`}
          >
            <p className="font-bold text-sm">{p.label}</p>
            <p className="text-xs text-[var(--text-secondary)]">{p.desc}</p>
          </button>
        ))}
      </div>

      <div className="surface-card border-red-200 p-6 space-y-3">
        <h2 className="font-bold text-sm text-red-900">Privacidad y Eliminación de Datos</h2>
        <p className="text-xs text-[var(--text-secondary)]">
          Anonimiza tus datos personales identificables conservando únicamente registros históricos anonimizados.
        </p>
        {!confirmAnon ? (
          <button
            type="button"
            onClick={() => setConfirmAnon(true)}
            className="rounded-lg border border-red-300 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50"
          >
            Solicitar anonimización de cuenta
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => void handleAnonymize()}
              className="rounded-lg bg-red-700 px-3 py-1.5 text-xs font-semibold text-white"
            >
              Confirmar anonimización irreversible
            </button>
            <button
              type="button"
              onClick={() => setConfirmAnon(false)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold"
            >
              Cancelar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
