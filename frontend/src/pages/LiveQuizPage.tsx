import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useParams, useSearchParams } from 'react-router-dom';
import { ArrowRight, Play, Radio, Trophy } from 'lucide-react';
import { ChallengeRenderer } from '../components/challenges/ChallengeRenderer';
import { ErrorBanner, LoadingState, SuccessBanner } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { LiveSessionStateOut } from '../types/api';

export function LiveQuizPage() {
  const { roomCode: paramCode } = useParams<{ roomCode?: string }>();
  const [searchParams] = useSearchParams();
  const isHost = searchParams.get('host') === '1';
  const { user } = useAppState();

  const [codeInput, setCodeInput] = useState(paramCode ?? '');
  const [activeCode, setActiveCode] = useState((paramCode ?? '').toUpperCase());
  const [displayName, setDisplayName] = useState(user?.full_name ?? '');
  const [participantId, setParticipantId] = useState<string | null>(null);
  const [answerFeedback, setAnswerFeedback] = useState<{ is_correct: boolean; points_awarded: number; explanation: string } | null>(null);

  const roomQuery = useQuery({
    queryKey: ['live-room', activeCode],
    queryFn: () => apiRequest<LiveSessionStateOut>(`/live-sessions/${activeCode}`, {}, false),
    enabled: activeCode.length >= 4,
    refetchInterval: 2000,
  });

  const joinMutation = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      return apiRequest<{ participant_id: string }>(`/live-sessions/${activeCode}/join`, {
        method: 'POST',
        body: JSON.stringify({ display_name: displayName }),
      }, false);
    },
    onSuccess: (res) => setParticipantId(res.participant_id),
  });

  const advanceMutation = useMutation({
    mutationFn: () =>
      apiRequest<LiveSessionStateOut>(`/live-sessions/${activeCode}/advance`, { method: 'POST' }),
    onSuccess: () => void roomQuery.refetch(),
  });

  const answerMutation = useMutation({
    mutationFn: (submitted_answer: Record<string, unknown>) =>
      apiRequest<{ is_correct: boolean; points_awarded: number; explanation: string }>(
        `/live-sessions/${activeCode}/answer`,
        {
          method: 'POST',
          body: JSON.stringify({ participant_id: participantId, submitted_answer }),
        },
        false
      ),
    onSuccess: (res) => {
      setAnswerFeedback(res);
      void roomQuery.refetch();
    },
  });

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="surface-card p-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-100 px-3 py-1 text-xs font-bold text-indigo-900">
            <Radio className="h-3.5 w-3.5" /> Clase en Vivo Vistazo
          </span>
          <h1 className="mt-2 text-xl font-bold">{roomQuery.data?.title || 'Unirse a una Sala en Vivo'}</h1>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setActiveCode(codeInput.trim().toUpperCase());
            setAnswerFeedback(null);
          }}
          className="flex gap-2"
        >
          <input
            placeholder="LIVE-XXXX"
            value={codeInput}
            onChange={(e) => setCodeInput(e.target.value.toUpperCase())}
            className="w-36 rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-xs font-mono uppercase"
          />
          <button type="submit" className="btn-primary px-4 py-2 text-xs font-semibold">
            Entrar
          </button>
        </form>
      </div>

      {roomQuery.isLoading && <LoadingState label="Conectando a sala en vivo..." />}
      {(roomQuery.error || joinMutation.error || advanceMutation.error || answerMutation.error) && (
        <ErrorBanner
          message={
            ((roomQuery.error || joinMutation.error || advanceMutation.error || answerMutation.error) as Error).message
          }
        />
      )}

      {roomQuery.data && (
        <>
          {isHost && (
            <div className="surface-card border-indigo-200 bg-indigo-50 p-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold text-indigo-950">
                  Sala: <span className="font-mono text-base">{roomQuery.data.room_code}</span> • Estado:{' '}
                  {roomQuery.data.status} ({roomQuery.data.current_index + 1}/{roomQuery.data.total_challenges})
                </p>
                <p className="text-xs text-indigo-800">
                  Comparte este código o el enlace {window.location.origin}/vivo/{roomQuery.data.room_code} con tu clase.
                </p>
              </div>
              {roomQuery.data.status !== 'finished' && (
                <button
                  type="button"
                  disabled={advanceMutation.isPending}
                  onClick={() => {
                    setAnswerFeedback(null);
                    advanceMutation.mutate();
                  }}
                  className="btn-primary inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold"
                >
                  {roomQuery.data.status === 'waiting' ? (
                    <>
                      <Play className="h-3.5 w-3.5" /> Iniciar Primera Pregunta
                    </>
                  ) : (
                    <>
                      Siguiente / Finalizar <ArrowRight className="h-3.5 w-3.5" />
                    </>
                  )}
                </button>
              )}
            </div>
          )}

          {!isHost && !participantId && roomQuery.data.status !== 'finished' && (
            <form onSubmit={joinMutation.mutate} className="surface-card p-5 space-y-3">
              <h2 className="text-base font-bold">Ingresa tu nombre para participar en vivo</h2>
              <div className="flex gap-2">
                <input
                  required
                  minLength={2}
                  placeholder="Tu nombre o alias en clase"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="flex-1 rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
                />
                <button type="submit" disabled={joinMutation.isPending} className="btn-primary px-5 py-2 text-xs font-bold">
                  Participar
                </button>
              </div>
            </form>
          )}

          {roomQuery.data.status === 'waiting' && (
            <div className="surface-card p-6 text-center text-sm text-[var(--text-secondary)]">
              Esperando a que el docente inicie la primera pregunta...
            </div>
          )}

          {roomQuery.data.status === 'active' && roomQuery.data.current_challenge && (participantId || isHost) && (
            <div className="surface-card p-6 space-y-4">
              <p className="text-xs font-bold text-[var(--brand-primary)]">
                Pregunta {roomQuery.data.current_index + 1} de {roomQuery.data.total_challenges}
              </p>
              <ChallengeRenderer
                key={`${roomQuery.data.current_challenge.id}-${roomQuery.data.current_index}`}
                challenge={roomQuery.data.current_challenge}
                disabled={isHost || answerMutation.isPending || Boolean(answerFeedback)}
                onSubmit={(ans) => answerMutation.mutate(ans)}
              />
              {answerFeedback && (
                <SuccessBanner
                  message={
                    answerFeedback.is_correct
                      ? `¡Correcto! +${answerFeedback.points_awarded} pts — ${answerFeedback.explanation}`
                      : `Incorrecto — ${answerFeedback.explanation}`
                  }
                />
              )}
            </div>
          )}

          <section className="surface-card p-5 space-y-3">
            <h3 className="flex items-center gap-2 text-sm font-bold">
              <Trophy className="h-4 w-4 text-amber-600" /> Marcador en Tiempo Real ({roomQuery.data.leaderboard.length})
            </h3>
            {roomQuery.data.leaderboard.length === 0 ? (
              <p className="text-xs text-[var(--text-secondary)]">Aún no hay participantes conectados.</p>
            ) : (
              <ul className="space-y-1.5 text-xs">
                {roomQuery.data.leaderboard.map((p, i) => (
                  <li key={p.id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                    <span className="font-semibold">
                      #{i + 1} {p.display_name}
                    </span>
                    <span className="font-bold text-[var(--brand-primary)]">
                      {p.score} pts ({p.correct_count}/{p.answered_count})
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
