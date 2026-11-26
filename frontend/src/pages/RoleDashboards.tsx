import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { EmptyState, ErrorBanner, LoadingState, SuccessBanner } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { ClassroomAnalytics, ClassroomOut, ClassroomStudentOut, UIProfile } from '../types/api';

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
    </div>
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
    </div>
  );
}

export function SuperAdminPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');

  const orgsQuery = useQuery({
    queryKey: ['admin-orgs'],
    queryFn: () =>
      apiRequest<{ id: string; name: string; slug: string; sector_type: string; default_ui_profile: string }[]>(
        '/admin/organizations'
      ),
  });

  const createOrg = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      return apiRequest('/admin/organizations', {
        method: 'POST',
        body: JSON.stringify({
          name,
          slug,
          sector_type: 'rescue_brigade',
          default_ui_profile: 'pro',
        }),
      });
    },
    onSuccess: () => {
      setName('');
      setSlug('');
      void queryClient.invalidateQueries({ queryKey: ['admin-orgs'] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="surface-card p-6">
        <h1 className="text-xl font-bold">Panel SuperAdministrador</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Alta global de organizaciones multi-tenant.</p>
      </div>

      {createOrg.error && <ErrorBanner message={(createOrg.error as Error).message} />}

      <form onSubmit={createOrg.mutate} className="surface-card grid gap-3 p-5 sm:grid-cols-3">
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
        <button type="submit" className="btn-primary px-4 py-2 text-sm font-semibold">
          Crear organización
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
    </div>
  );
}

export function ProfilePage() {
  const { user, uiProfile, setUiProfile } = useAppState();
  if (!user) return null;

  const profiles: { id: UIProfile; label: string; desc: string }[] = [
    { id: 'kids', label: 'Infantil y Primaria', desc: 'Mayor espaciado táctil y tonos cálidos.' },
    { id: 'youth', label: 'Juvenil y Secundaria', desc: 'Contraste vibrante para micro-retos dinámicos.' },
    { id: 'pro', label: 'Profesional / Universitario / Rescate', desc: 'Sobrio, técnico y de máxima legibilidad operativa.' },
  ];

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
    </div>
  );
}
