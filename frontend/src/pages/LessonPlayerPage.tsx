import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Lightbulb, WifiOff, XCircle } from 'lucide-react';
import { ChallengeRenderer } from '../components/challenges/ChallengeRenderer';
import { EmptyState, ErrorBanner, LoadingState, SuccessBanner } from '../components/ui/StatusStates';
import { enqueueOfflineAttempt } from '../pwa/offlineQueue';
import { ApiError, apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { AttemptResult, ChallengePublic, SocraticHintResponse } from '../types/api';

export function LessonPlayerPage() {
  const { lessonVersionId } = useParams<{ lessonVersionId: string }>();
  const [searchParams] = useSearchParams();
  const classroomId = searchParams.get('classroomId');
  const { user } = useAppState();

  const [index, setIndex] = useState(0);
  const [lastResult, setLastResult] = useState<AttemptResult | null>(null);
  const [offlineSavedMsg, setOfflineSavedMsg] = useState<string | null>(null);
  const [failedCounts, setFailedCounts] = useState<Record<string, number>>({});
  const [socraticHint, setSocraticHint] = useState<SocraticHintResponse | null>(null);
  const [startedAt, setStartedAt] = useState<number>(Date.now());

  const { data: challenges, isLoading, error, refetch } = useQuery({
    queryKey: ['lesson-challenges', lessonVersionId],
    queryFn: () => apiRequest<ChallengePublic[]>(`/lesson-versions/${lessonVersionId}/challenges`),
    enabled: Boolean(lessonVersionId),
  });

  const submitMutation = useMutation({
    mutationFn: async ({ challengeId, answer }: { challengeId: string; answer: Record<string, unknown> }) => {
      const attemptId = crypto.randomUUID();
      const responseTime = Date.now() - startedAt;
      if (!navigator.onLine) {
        await enqueueOfflineAttempt({
          client_attempt_id: attemptId,
          challenge_id: challengeId,
          classroom_id: classroomId,
          submitted_answer: answer,
          response_time_ms: responseTime,
          queued_at: Date.now(),
        });
        return null;
      }
      try {
        return await apiRequest<AttemptResult>(`/challenges/${challengeId}/attempt`, {
          method: 'POST',
          body: JSON.stringify({
            client_attempt_id: attemptId,
            classroom_id: classroomId,
            submitted_answer: answer,
            response_time_ms: responseTime,
          }),
        });
      } catch (err) {
        if (err instanceof ApiError && err.status === 0) {
          await enqueueOfflineAttempt({
            client_attempt_id: attemptId,
            challenge_id: challengeId,
            classroom_id: classroomId,
            submitted_answer: answer,
            response_time_ms: responseTime,
            queued_at: Date.now(),
          });
          return null;
        }
        throw err;
      }
    },
    onSuccess: (res) => {
      if (res === null) {
        setOfflineSavedMsg('Sin conexión: intento guardado localmente para sincronizar al volver la red.');
        return;
      }
      setOfflineSavedMsg(null);
      setLastResult(res);
      if (!res.is_correct) {
        setFailedCounts((prev) => ({
          ...prev,
          [res.challenge_id]: (prev[res.challenge_id] ?? 0) + 1,
        }));
      }
    },
  });

  const hintMutation = useMutation({
    mutationFn: (challengeId: string) =>
      apiRequest<SocraticHintResponse>(`/challenges/${challengeId}/socratic-hint`, {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    onSuccess: (res) => setSocraticHint(res),
  });

  if (isLoading) return <LoadingState label="Preparando retos de la lección..." />;
  if (error) return <ErrorBanner message={(error as Error).message} onRetry={() => void refetch()} />;
  if (!challenges || challenges.length === 0) {
    return <EmptyState title="Sin retos publicados" description="Esta versión de lección aún no contiene retos." />;
  }

  const current = challenges[index];
  const isLast = index === challenges.length - 1;
  const pct = Math.round(((index + (lastResult || offlineSavedMsg ? 1 : 0)) / challenges.length) * 100);
  const currentFailures = failedCounts[current.id] ?? 0;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div className="surface-card p-4">
        <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
          <span>
            Reto {index + 1} de {challenges.length}
          </span>
          <span>{pct}%</span>
        </div>
        <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-slate-200">
          <div className="h-full bg-[var(--brand-primary)] transition-all" style={{ width: `${pct}%` }} />
        </div>
      </div>

      {!user && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-3.5 text-xs text-amber-950">
          Estás viendo la lección en modo vista previa.{' '}
          <Link to="/login" className="font-bold underline">
            Inicia sesión
          </Link>{' '}
          para evaluar tus respuestas y guardar tu progreso.
        </div>
      )}

      <div className="surface-card p-6">
        <ChallengeRenderer
          key={current.id}
          challenge={current}
          disabled={!user || submitMutation.isPending}
          onSubmit={(answer) => submitMutation.mutate({ challengeId: current.id, answer })}
        />

        {submitMutation.error && (
          <div className="mt-4">
            <ErrorBanner message={(submitMutation.error as Error).message} />
          </div>
        )}

        {offlineSavedMsg && (
          <div className="mt-4 space-y-3">
            <SuccessBanner message={offlineSavedMsg} />
            {!isLast && (
              <button
                type="button"
                onClick={() => {
                  setIndex((i) => i + 1);
                  setOfflineSavedMsg(null);
                  setStartedAt(Date.now());
                }}
                className="btn-primary inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold"
              >
                <WifiOff className="h-3.5 w-3.5" /> Continuar sin conexión
              </button>
            )}
          </div>
        )}

        {user && currentFailures >= 2 && (
          <div className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="flex items-center gap-1.5 text-xs font-bold text-indigo-900">
                <Lightbulb className="h-4 w-4 text-indigo-600" /> Tutor Socrático disponible
              </span>
              <button
                type="button"
                disabled={hintMutation.isPending}
                onClick={() => hintMutation.mutate(current.id)}
                className="rounded-lg bg-indigo-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-800"
              >
                {hintMutation.isPending ? 'Pensando pista...' : 'Solicitar pista guía'}
              </button>
            </div>
            {hintMutation.error && (
              <p className="mt-2 text-xs text-red-700">{(hintMutation.error as Error).message}</p>
            )}
            {socraticHint && <p className="mt-2 text-sm text-indigo-950">{socraticHint.hint}</p>}
          </div>
        )}

        {lastResult && (
          <div
            className={`mt-5 rounded-xl border p-4 ${
              lastResult.is_correct ? 'border-emerald-300 bg-emerald-50 text-emerald-950' : 'border-red-300 bg-red-50 text-red-950'
            }`}
          >
            <div className="flex items-center gap-2 font-bold text-sm">
              {lastResult.is_correct ? (
                <>
                  <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                  ¡Correcto! +{lastResult.score_awarded} pts
                </>
              ) : (
                <>
                  <XCircle className="h-5 w-5 text-red-600" />
                  Respuesta incorrecta (0 / {lastResult.max_points} pts)
                </>
              )}
            </div>
            <p className="mt-2 text-sm">{lastResult.pedagogical_explanation}</p>
            <p className="mt-2 text-xs font-semibold">
              Progreso de lección: {lastResult.completed_challenges}/{lastResult.total_challenges} ({lastResult.lesson_score_pct}%)
            </p>

            {!isLast ? (
              <button
                type="button"
                onClick={() => {
                  setIndex((i) => i + 1);
                  setLastResult(null);
                  setSocraticHint(null);
                  setStartedAt(Date.now());
                }}
                className="btn-primary mt-4 inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold"
              >
                Siguiente reto <ArrowRight className="h-4 w-4" />
              </button>
            ) : (
              <Link
                to="/dashboard"
                className="btn-primary mt-4 inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold"
              >
                Finalizar y ver mi progreso
              </Link>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
