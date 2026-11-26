import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowRight, CheckCircle2, XCircle } from 'lucide-react';
import { ChallengeRenderer } from '../components/challenges/ChallengeRenderer';
import { EmptyState, ErrorBanner, LoadingState } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { AttemptResult, ChallengePublic } from '../types/api';

export function LessonPlayerPage() {
  const { lessonVersionId } = useParams<{ lessonVersionId: string }>();
  const [searchParams] = useSearchParams();
  const classroomId = searchParams.get('classroomId');
  const { user } = useAppState();

  const [index, setIndex] = useState(0);
  const [lastResult, setLastResult] = useState<AttemptResult | null>(null);
  const [startedAt, setStartedAt] = useState<number>(Date.now());

  const { data: challenges, isLoading, error, refetch } = useQuery({
    queryKey: ['lesson-challenges', lessonVersionId],
    queryFn: () => apiRequest<ChallengePublic[]>(`/lesson-versions/${lessonVersionId}/challenges`),
    enabled: Boolean(lessonVersionId),
  });

  const submitMutation = useMutation({
    mutationFn: ({ challengeId, answer }: { challengeId: string; answer: Record<string, unknown> }) =>
      apiRequest<AttemptResult>(`/challenges/${challengeId}/attempt`, {
        method: 'POST',
        body: JSON.stringify({
          client_attempt_id: crypto.randomUUID(),
          classroom_id: classroomId,
          submitted_answer: answer,
          response_time_ms: Date.now() - startedAt,
        }),
      }),
    onSuccess: (res) => {
      setLastResult(res);
    },
  });

  if (isLoading) return <LoadingState label="Preparando retos de la lección..." />;
  if (error) return <ErrorBanner message={(error as Error).message} onRetry={() => void refetch()} />;
  if (!challenges || challenges.length === 0) {
    return <EmptyState title="Sin retos publicados" description="Esta versión de lección aún no contiene retos." />;
  }

  const current = challenges[index];
  const isLast = index === challenges.length - 1;
  const pct = Math.round(((index + (lastResult ? 1 : 0)) / challenges.length) * 100);

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
