import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowRight, Brain, CheckCircle2, Clock, Flame, Lightbulb, Sparkles, WifiOff, XCircle } from 'lucide-react';
import { ChallengeRenderer } from '../components/challenges/ChallengeRenderer';
import { EmptyState, ErrorBanner, LoadingState, SuccessBanner } from '../components/ui/StatusStates';
import { enqueueOfflineAttempt } from '../pwa/offlineQueue';
import { ApiError, apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type {
  AdaptiveRemediationResponse,
  AttemptResult,
  ChallengePublic,
  LessonPlayerContextOut,
  SocraticHintResponse,
} from '../types/api';

function formatClock(totalSeconds: number): string {
  const safe = Math.max(0, totalSeconds);
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export function LessonPlayerPage() {
  const { lessonVersionId } = useParams<{ lessonVersionId: string }>();
  const [searchParams] = useSearchParams();
  const classroomId = searchParams.get('classroomId');
  const { user } = useAppState();

  const [index, setIndex] = useState(0);
  const [lastResult, setLastResult] = useState<AttemptResult | null>(null);
  const [offlineSavedMsg, setOfflineSavedMsg] = useState<string | null>(null);
  const [failedCounts, setFailedCounts] = useState<Record<string, number>>({});
  const [missedPrompts, setMissedPrompts] = useState<string[]>([]);
  const [socraticHint, setSocraticHint] = useState<SocraticHintResponse | null>(null);
  const [startedAt, setStartedAt] = useState<number>(Date.now());
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);
  const [remediation, setRemediation] = useState<AdaptiveRemediationResponse | null>(null);

  const contextQuery = useQuery({
    queryKey: ['lesson-context', lessonVersionId],
    queryFn: () => apiRequest<LessonPlayerContextOut>(`/lesson-versions/${lessonVersionId}/context`),
    enabled: Boolean(lessonVersionId),
  });

  const { data: challenges, isLoading, error, refetch } = useQuery({
    queryKey: ['lesson-challenges', lessonVersionId],
    queryFn: () => apiRequest<ChallengePublic[]>(`/lesson-versions/${lessonVersionId}/challenges`),
    enabled: Boolean(lessonVersionId),
  });

  const isStrongExam = contextQuery.data?.lesson_type === 'strong_exam';

  useEffect(() => {
    if (isStrongExam && contextQuery.data && secondsLeft === null) {
      setSecondsLeft(contextQuery.data.estimated_minutes * 60);
    }
  }, [isStrongExam, contextQuery.data, secondsLeft]);

  useEffect(() => {
    if (!isStrongExam || secondsLeft === null || secondsLeft <= 0) return;
    const id = window.setInterval(() => {
      setSecondsLeft((prev) => (prev !== null && prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => window.clearInterval(id);
  }, [isStrongExam, secondsLeft]);

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
        const curPrompt = challenges?.[index]?.prompt;
        if (curPrompt) {
          setMissedPrompts((prev) => (prev.includes(curPrompt) ? prev : [...prev, curPrompt]));
        }
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

  const remediationMutation = useMutation({
    mutationFn: () =>
      apiRequest<AdaptiveRemediationResponse>('/ai/adaptive-remediation', {
        method: 'POST',
        body: JSON.stringify({
          course_id: contextQuery.data?.course_id ?? null,
          missed_prompts: missedPrompts,
        }),
      }),
    onSuccess: (res) => setRemediation(res),
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
  const examScoreNum = lastResult ? Number(lastResult.lesson_score_pct) : 0;
  const passingTarget = contextQuery.data?.passing_score_pct ?? 70;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div className="surface-card p-4 space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-semibold text-[var(--text-secondary)]">
          <div className="flex items-center gap-2">
            <span>
              Reto {index + 1} de {challenges.length}
            </span>
            {isStrongExam && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-[11px] font-bold text-amber-950">
                <Flame className="h-3 w-3 text-amber-600" /> Modo Prueba Fuerte (Min {passingTarget}%)
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {isStrongExam && secondsLeft !== null && (
              <span
                className={`inline-flex items-center gap-1 rounded px-2 py-0.5 font-mono font-bold ${
                  secondsLeft <= 60 ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-800'
                }`}
              >
                <Clock className="h-3.5 w-3.5" /> {formatClock(secondsLeft)}
              </span>
            )}
            <span>{pct}%</span>
          </div>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200">
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

        {/* Tutor Socrático deshabilitado durante Prueba Fuerte real */}
        {user && !isStrongExam && currentFailures >= 2 && (
          <div className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="flex items-center gap-1.5 text-xs font-bold text-indigo-900">
                <Lightbulb className="h-4 w-4 text-indigo-600" /> Tutor Socrático disponible (conectado a tu guía)
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
            {hintMutation.error && <p className="mt-2 text-xs text-red-700">{(hintMutation.error as Error).message}</p>}
            {socraticHint && <p className="mt-2 text-sm text-indigo-950">{socraticHint.hint}</p>}
          </div>
        )}

        {lastResult && (
          <div
            className={`mt-5 rounded-xl border p-4 ${
              lastResult.is_correct
                ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                : 'border-red-300 bg-red-50 text-red-950'
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
              Progreso: {lastResult.completed_challenges}/{lastResult.total_challenges} ({lastResult.lesson_score_pct}%)
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
              <div className="mt-4 space-y-3 border-t border-black/10 pt-3">
                {isStrongExam && (
                  <div className="rounded-lg bg-white/90 p-3 text-xs text-slate-900">
                    <p className="font-bold">
                      Diagnóstico de Prueba Fuerte:{' '}
                      {examScoreNum >= passingTarget ? 'APROBADO' : 'REQUIERE REFUERZO'} ({examScoreNum}% / mín.{' '}
                      {passingTarget}%)
                    </p>
                    {missedPrompts.length > 0 && (
                      <p className="mt-1 text-[var(--text-secondary)]">
                        {missedPrompts.length} conceptos fallados enviados a tu cola de Repaso Espaciado SM-2.
                      </p>
                    )}
                  </div>
                )}

                <div className="flex flex-wrap gap-2">
                  <Link
                    to="/dashboard"
                    className="btn-primary inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold"
                  >
                    Finalizar y ver mi progreso
                  </Link>
                  {missedPrompts.length > 0 && (
                    <>
                      <button
                        type="button"
                        disabled={remediationMutation.isPending}
                        onClick={() => remediationMutation.mutate()}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-700 px-3.5 py-2 text-xs font-semibold text-white hover:bg-indigo-800"
                      >
                        <Sparkles className="h-3.5 w-3.5" />
                        {remediationMutation.isPending ? 'Creando guía...' : 'Generar Refuerzo IA con mis fallos'}
                      </button>
                      <Link
                        to="/reviews"
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-900"
                      >
                        <Brain className="h-3.5 w-3.5" /> Ir a Repaso SM-2
                      </Link>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {remediation && (
          <div className="mt-5 rounded-xl border border-indigo-200 bg-indigo-50 p-4 space-y-2">
            <h3 className="text-sm font-bold text-indigo-950">{remediation.title}</h3>
            <pre className="whitespace-pre-wrap font-sans text-xs text-indigo-900">
              {remediation.remediation_markdown}
            </pre>
            {remediation.action_steps.length > 0 && (
              <ul className="list-disc pl-5 text-xs text-indigo-950">
                {remediation.action_steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
