import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BatteryCharging, Brain, CheckCircle2, RotateCcw } from 'lucide-react';
import { ChallengeRenderer } from '../components/challenges/ChallengeRenderer';
import { EmptyState, ErrorBanner, LoadingState, SuccessBanner } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { AttemptResult, ChallengePublic, DueReviewItem, ReviewSessionOut } from '../types/api';

export function SpacedReviewPage() {
  const { user, activeOrg } = useAppState();
  const queryClient = useQueryClient();
  const [activeSession, setActiveSession] = useState<ReviewSessionOut | null>(null);
  const [itemIndex, setItemIndex] = useState(0);
  const [lastAttempt, setLastAttempt] = useState<AttemptResult | null>(null);
  const [completedBanner, setCompletedBanner] = useState<string | null>(null);

  const dueQuery = useQuery({
    queryKey: ['due-reviews', activeOrg?.organization_id],
    queryFn: () =>
      apiRequest<DueReviewItem[]>(
        `/reviews/due${activeOrg ? `?organization_id=${activeOrg.organization_id}` : ''}`
      ),
    enabled: Boolean(user),
  });

  const startSession = useMutation({
    mutationFn: (mode: 'spaced_repetition' | 'energy_recovery') =>
      apiRequest<ReviewSessionOut>('/reviews/sessions', {
        method: 'POST',
        body: JSON.stringify({
          organization_id: activeOrg?.organization_id ?? null,
          session_mode: mode,
          limit: 5,
        }),
      }),
    onSuccess: (session) => {
      setActiveSession(session);
      setItemIndex(0);
      setLastAttempt(null);
      setCompletedBanner(null);
    },
  });

  const submitAttempt = useMutation({
    mutationFn: ({ challengeId, answer }: { challengeId: string; answer: Record<string, unknown> }) =>
      apiRequest<AttemptResult>(`/challenges/${challengeId}/attempt`, {
        method: 'POST',
        body: JSON.stringify({
          client_attempt_id: crypto.randomUUID(),
          submitted_answer: answer,
        }),
      }),
    onSuccess: (res) => {
      setLastAttempt(res);
    },
  });

  const completeSession = useMutation({
    mutationFn: ({ sessionId, count }: { sessionId: string; count: number }) =>
      apiRequest<ReviewSessionOut>(`/reviews/sessions/${sessionId}/complete`, {
        method: 'POST',
        body: JSON.stringify({ items_completed: count }),
      }),
    onSuccess: (res) => {
      setActiveSession(null);
      setCompletedBanner(
        res.energy_recovered > 0
          ? `Sesión completada (+15 XP y +${res.energy_recovered} energía recuperada).`
          : 'Sesión de repaso espaciado completada (+15 XP).'
      );
      void queryClient.invalidateQueries({ queryKey: ['due-reviews'] });
      void queryClient.invalidateQueries({ queryKey: ['gamification-me'] });
    },
  });

  if (!user) {
    return <EmptyState title="Inicia sesión para repasar" description="El motor SM-2 guarda tu memoria por reto." />;
  }

  if (activeSession && activeSession.items.length > 0) {
    const currentItem = activeSession.items[itemIndex];
    const asChallenge: ChallengePublic = {
      id: currentItem.challenge_id,
      lesson_version_id: currentItem.challenge_id,
      competency_id: null,
      challenge_type: currentItem.challenge_type,
      schema_version: 1,
      order_index: itemIndex,
      prompt: currentItem.prompt,
      payload_json: currentItem.payload_json,
      difficulty: 2,
      points: currentItem.points,
      estimated_seconds: currentItem.estimated_seconds,
      is_safety_critical: currentItem.is_safety_critical,
      status: 'published',
    };
    const isLast = itemIndex === activeSession.items.length - 1;

    return (
      <div className="mx-auto max-w-2xl space-y-5">
        <div className="surface-card flex items-center justify-between p-4 text-xs font-semibold">
          <span>
            Repaso {itemIndex + 1} de {activeSession.items.length} ({currentItem.item_state})
          </span>
          <span>Intervalo previo: {currentItem.interval_days} días</span>
        </div>
        <div className="surface-card p-6">
          <ChallengeRenderer
            key={currentItem.challenge_id}
            challenge={asChallenge}
            disabled={submitAttempt.isPending}
            onSubmit={(answer) => submitAttempt.mutate({ challengeId: currentItem.challenge_id, answer })}
          />
          {lastAttempt && (
            <div className="mt-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-accent-soft)] p-4">
              <p className="font-bold text-sm">
                {lastAttempt.is_correct ? '¡Recuperación exitosa!' : 'Refuerzo programado'}
              </p>
              <p className="mt-1 text-sm">{lastAttempt.pedagogical_explanation}</p>
              {!isLast ? (
                <button
                  type="button"
                  onClick={() => {
                    setItemIndex((i) => i + 1);
                    setLastAttempt(null);
                  }}
                  className="btn-primary mt-3 px-4 py-2 text-xs font-semibold"
                >
                  Siguiente ítem
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() =>
                    completeSession.mutate({
                      sessionId: activeSession.session_id,
                      count: activeSession.items.length,
                    })
                  }
                  className="btn-primary mt-3 px-4 py-2 text-xs font-semibold"
                >
                  Finalizar sesión
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="surface-card flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold">
            <Brain className="h-5 w-5 text-[var(--brand-primary)]" /> Repaso Espaciado (SM-2)
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Retos priorizados por curva de olvido y refresco periódico de seguridad crítica (máx. 45 días).
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={startSession.isPending}
            onClick={() => startSession.mutate('spaced_repetition')}
            className="btn-primary inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold"
          >
            <RotateCcw className="h-4 w-4" /> Iniciar repaso activo
          </button>
          <button
            type="button"
            disabled={startSession.isPending}
            onClick={() => startSession.mutate('energy_recovery')}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-white px-4 py-2 text-xs font-semibold hover:bg-slate-50"
          >
            <BatteryCharging className="h-4 w-4 text-emerald-600" /> Recuperar energía
          </button>
        </div>
      </div>

      {completedBanner && <SuccessBanner message={completedBanner} />}
      {dueQuery.isLoading ? (
        <LoadingState label="Consultando ítems vencidos..." />
      ) : dueQuery.error ? (
        <ErrorBanner message={(dueQuery.error as Error).message} onRetry={() => void dueQuery.refetch()} />
      ) : !dueQuery.data?.length ? (
        <EmptyState
          title="Sin repasos vencidos por ahora"
          description="Completa lecciones o practica con tu Biblioteca Visual en Entrenamiento Flash."
        />
      ) : (
        <div className="space-y-2.5">
          {dueQuery.data.map((item) => (
            <div key={item.sr_item_id} className="surface-card flex items-center justify-between p-4">
              <div>
                <p className="font-semibold text-sm">{item.prompt}</p>
                <p className="text-xs text-[var(--text-secondary)]">
                  Estado: {item.item_state} • Fallos previos: {item.lapses}
                </p>
              </div>
              <CheckCircle2 className="h-5 w-5 text-[var(--brand-primary)]" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
