import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BatteryCharging, BookMarked, Brain, CheckCircle2, Download, Plus, RotateCcw, Trash2, Upload } from 'lucide-react';
import { ChallengeRenderer } from '../components/challenges/ChallengeRenderer';
import { EmptyState, ErrorBanner, LoadingState, SuccessBanner } from '../components/ui/StatusStates';
import { API_BASE, apiRequest, getAccessToken } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { AttemptResult, ChallengePublic, DueReviewItem, NoteOut, ReviewSessionOut } from '../types/api';

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

      <NotesAndFlashcardsSection />
    </div>
  );
}

function NotesAndFlashcardsSection() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [isFlashcard, setIsFlashcard] = useState(true);
  const [csvImport, setCsvImport] = useState('');
  const [showImport, setShowImport] = useState(false);

  const notesQuery = useQuery({
    queryKey: ['student-notes'],
    queryFn: () => apiRequest<NoteOut[]>('/notes/me'),
  });

  const createNote = useMutation({
    mutationFn: () =>
      apiRequest<NoteOut>('/notes/me', {
        method: 'POST',
        body: JSON.stringify({ title: title.trim(), content: content.trim(), is_flashcard: isFlashcard }),
      }),
    onSuccess: () => {
      setTitle('');
      setContent('');
      queryClient.invalidateQueries({ queryKey: ['student-notes'] });
    },
  });

  const deleteNote = useMutation({
    mutationFn: (id: string) => apiRequest<void>(`/notes/me/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['student-notes'] }),
  });

  const importCsv = useMutation({
    mutationFn: () =>
      apiRequest<NoteOut[]>('/notes/me/import-csv', {
        method: 'POST',
        body: JSON.stringify({ csv_text: csvImport }),
      }),
    onSuccess: () => {
      setCsvImport('');
      setShowImport(false);
      queryClient.invalidateQueries({ queryKey: ['student-notes'] });
    },
  });

  const handleExportCsv = async () => {
    const token = getAccessToken();
    const res = await fetch(`${API_BASE}/notes/me/flashcards-csv`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: 'include',
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'vistazo-flashcards-anki.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="surface-card p-6 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-bold">
            <BookMarked className="h-5 w-5 text-[var(--brand-primary)]" /> Apuntes Personales y Flashcards (Anki CSV)
          </h2>
          <p className="text-xs text-[var(--text-secondary)]">
            Guarda resúmenes clave, convierte conceptos en tarjetas de estudio e impórtalas o expórtalas a Anki.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void handleExportCsv()}
            className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-1.5 text-xs font-semibold hover:bg-slate-50"
          >
            <Download className="h-3.5 w-3.5" /> Exportar CSV
          </button>
          <button
            type="button"
            onClick={() => setShowImport((v) => !v)}
            className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-1.5 text-xs font-semibold hover:bg-slate-50"
          >
            <Upload className="h-3.5 w-3.5" /> Importar CSV
          </button>
        </div>
      </div>

      {showImport && (
        <div className="rounded-xl border border-[var(--border-subtle)] bg-slate-50 p-3.5 space-y-2">
          <p className="text-xs font-semibold">Pega tus tarjetas en formato CSV (Frente,Reverso por línea):</p>
          <textarea
            rows={4}
            value={csvImport}
            onChange={(e) => setCsvImport(e.target.value)}
            placeholder={'Front,Back\n"Mitocondria","Central energética de la célula"'}
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-white p-2.5 text-xs font-mono"
          />
          <button
            type="button"
            disabled={!csvImport.trim() || importCsv.isPending}
            onClick={() => importCsv.mutate()}
            className="btn-primary px-4 py-1.5 text-xs font-semibold disabled:opacity-50"
          >
            Confirmar importación CSV
          </button>
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (title.trim() && content.trim()) createNote.mutate();
        }}
        className="grid gap-2.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-accent-soft)]/40 p-4 sm:grid-cols-3"
      >
        <input
          type="text"
          required
          placeholder="Concepto / Frente de tarjeta"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
        />
        <input
          type="text"
          required
          placeholder="Explicación / Reverso"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm sm:col-span-2"
        />
        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--text-secondary)]">
          <input
            type="checkbox"
            checked={isFlashcard}
            onChange={(e) => setIsFlashcard(e.target.checked)}
          />
          Incluir como Flashcard Anki
        </label>
        <div className="sm:col-span-2 flex justify-end">
          <button
            type="submit"
            disabled={createNote.isPending}
            className="btn-primary inline-flex items-center gap-1 px-4 py-2 text-xs font-semibold"
          >
            <Plus className="h-3.5 w-3.5" /> Guardar apunte
          </button>
        </div>
      </form>

      <div className="grid gap-2.5 sm:grid-cols-2">
        {(notesQuery.data ?? []).map((note) => (
          <div key={note.id} className="rounded-xl border border-[var(--border-subtle)] bg-white p-3.5">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-bold">{note.title}</p>
                <p className="mt-1 text-xs text-[var(--text-secondary)] whitespace-pre-wrap">{note.content}</p>
              </div>
              <button
                type="button"
                aria-label="Eliminar apunte"
                onClick={() => deleteNote.mutate(note.id)}
                className="text-slate-400 hover:text-rose-600"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
            {note.is_flashcard && (
              <span className="mt-2 inline-block rounded-full bg-[var(--bg-accent-soft)] px-2 py-0.5 text-[10px] font-semibold text-[var(--brand-primary)]">
                Flashcard
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
