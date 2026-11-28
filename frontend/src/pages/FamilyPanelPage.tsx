import { FormEvent, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Award, Flame, HeartHandshake, KeyRound, ShieldCheck } from 'lucide-react';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { GuardianSummaryOut } from '../types/api';

export function FamilyPanelPage() {
  const { user } = useAppState();
  const [codeInput, setCodeInput] = useState('');
  const [activeCode, setActiveCode] = useState('');

  const myCodeQuery = useQuery({
    queryKey: ['my-family-code'],
    queryFn: () => apiRequest<{ family_access_code: string }>('/auth/me/family-code'),
    enabled: Boolean(user),
  });

  const lookupMutation = useMutation({
    mutationFn: (code: string) =>
      apiRequest<GuardianSummaryOut>(`/auth/guardian/summary?code=${encodeURIComponent(code.trim().toUpperCase())}`),
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const cleaned = codeInput.trim().toUpperCase();
    if (!cleaned) return;
    setActiveCode(cleaned);
    lookupMutation.mutate(cleaned);
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="surface-card p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="flex items-center gap-2 text-xl font-bold">
              <HeartHandshake className="h-5 w-5 text-[var(--brand-primary)]" /> Portal de Familias y Tutores
            </h1>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Consulta progreso, racha diaria y cumplimiento de metas sin exponer datos personales sensibles (modo privacidad para menores).
            </p>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
            <ShieldCheck className="h-3.5 w-3.5" /> Privacidad COPPA / Solo métricas
          </span>
        </div>

        {user && myCodeQuery.data && (
          <div className="mt-4 rounded-xl border border-dashed border-[var(--brand-primary)]/40 bg-[var(--bg-accent-soft)] p-4">
            <p className="text-xs font-semibold text-[var(--text-secondary)]">
              Tu código familiar personal (compártelo con tu padre, madre o tutor):
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <code className="rounded-lg bg-white px-3 py-1.5 text-base font-bold tracking-widest text-[var(--brand-primary)]">
                {myCodeQuery.data.family_access_code}
              </code>
              <button
                type="button"
                onClick={() => {
                  setCodeInput(myCodeQuery.data.family_access_code);
                  setActiveCode(myCodeQuery.data.family_access_code);
                  lookupMutation.mutate(myCodeQuery.data.family_access_code);
                }}
                className="text-xs font-semibold text-[var(--brand-primary)] underline"
              >
                Previsualizar vista de tutor
              </button>
            </div>
          </div>
        )}
      </div>

      <form data-tour="family-code-form" onSubmit={handleSubmit} className="surface-card p-6">
        <label className="block text-sm font-semibold">
          Código de acceso familiar del estudiante
          <div className="mt-2 flex flex-wrap gap-2">
            <div className="relative flex-1 min-w-[220px]">
              <KeyRound className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-[var(--text-secondary)]" />
              <input
                type="text"
                required
                placeholder="Ej. FAM-A1B2C3D4"
                value={codeInput}
                onChange={(e) => setCodeInput(e.target.value)}
                className="w-full rounded-xl border border-[var(--border-subtle)] bg-white py-2 pl-9 pr-3 text-sm uppercase tracking-wider"
              />
            </div>
            <button
              type="submit"
              disabled={lookupMutation.isPending}
              className="btn-primary px-5 py-2 text-sm font-semibold disabled:opacity-50"
            >
              {lookupMutation.isPending ? 'Consultando...' : 'Ver resumen familiar'}
            </button>
          </div>
        </label>
        {lookupMutation.isError && (
          <p className="mt-3 text-xs font-semibold text-rose-600">
            Código no encontrado o inválido ({activeCode}). Verifica con el estudiante.
          </p>
        )}
      </form>

      {lookupMutation.data && (
        <div className="surface-card p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                Estudiante (iniciales protegidas)
              </p>
              <p className="text-2xl font-extrabold text-[var(--brand-primary)]">
                {lookupMutation.data.student_initials}
              </p>
            </div>
            <span className="rounded-full bg-[var(--bg-accent-soft)] px-3 py-1 text-xs font-semibold">
              Estado consentimiento: {lookupMutation.data.consent_status}
            </span>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-[var(--border-subtle)] p-4">
              <p className="text-xs text-[var(--text-secondary)]">XP Acumulado</p>
              <p className="mt-1 text-2xl font-bold">{lookupMutation.data.total_xp}</p>
            </div>
            <div className="rounded-xl border border-[var(--border-subtle)] p-4">
              <p className="flex items-center gap-1 text-xs text-[var(--text-secondary)]">
                <Flame className="h-3.5 w-3.5 text-amber-500" /> Racha actual
              </p>
              <p className="mt-1 text-2xl font-bold">
                {lookupMutation.data.current_streak_days} días
              </p>
              <p className="text-[11px] text-[var(--text-secondary)]">
                Máxima: {lookupMutation.data.longest_streak_days} días
              </p>
            </div>
            <div className="rounded-xl border border-[var(--border-subtle)] p-4">
              <p className="text-xs text-[var(--text-secondary)]">Lecciones completadas</p>
              <p className="mt-1 text-2xl font-bold">
                {lookupMutation.data.completed_lessons_count}
              </p>
              <p className="text-[11px] text-[var(--text-secondary)]">
                Meta diaria: {lookupMutation.data.daily_goal_minutes} min
              </p>
            </div>
            <div className="rounded-xl border border-[var(--border-subtle)] p-4">
              <p className="flex items-center gap-1 text-xs text-[var(--text-secondary)]">
                <Award className="h-3.5 w-3.5 text-[var(--brand-primary)]" /> Insignias ganadas
              </p>
              <p className="mt-1 text-2xl font-bold">{lookupMutation.data.badges_count}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
