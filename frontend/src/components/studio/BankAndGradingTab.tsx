import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckSquare, Database, Plus, Shuffle, Trash2 } from 'lucide-react';
import { EmptyState, ErrorBanner, LoadingState, SuccessBanner } from '../ui/StatusStates';
import { apiRequest } from '../../services/apiClient';
import type { OpenSubmissionOut, QuestionBankOut } from '../../types/api';
import { scopePrefix, type StudioScope } from './studioHelpers';

interface Props {
  scope: StudioScope;
  selectedLessonVersionId: string;
}

export function BankAndGradingTab({ scope, selectedLessonVersionId }: Props) {
  const queryClient = useQueryClient();
  const prefix = scopePrefix(scope);
  const [feedback, setFeedback] = useState<string | null>(null);

  // Nuevo ítem del Banco de Preguntas
  const [topicTag, setTopicTag] = useState('general');
  const [itemType, setItemType] = useState<'visual_concept_card' | 'open_response'>('visual_concept_card');
  const [prompt, setPrompt] = useState('');
  const [correctOpt, setCorrectOpt] = useState('Respuesta verificada');
  const [wrongOpt, setWrongOpt] = useState('Distractor común');
  const [rubricWords, setRubricWords] = useState('concepto, análisis, evidencia');
  const [explanation, setExplanation] = useState('Revisa los fundamentos clave de esta unidad.');
  const [points, setPoints] = useState(15);

  // Extraer del banco hacia la versión seleccionada
  const [pullCount, setPullCount] = useState(3);
  const [pullTopic, setPullTopic] = useState('');

  // Calificación docente de respuestas abiertas
  const [scoresMap, setScoresMap] = useState<Record<string, number>>({});
  const [notesMap, setNotesMap] = useState<Record<string, string>>({});

  const bankQuery = useQuery({
    queryKey: ['studio-question-bank', prefix],
    queryFn: () => apiRequest<QuestionBankOut[]>(`${prefix}/question-bank`),
  });

  const submissionsQuery = useQuery({
    queryKey: ['studio-open-submissions', prefix],
    queryFn: () => apiRequest<OpenSubmissionOut[]>(`${prefix}/open-submissions`),
  });

  const createBankItem = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      const payload_json =
        itemType === 'open_response'
          ? {
              instruction: 'Explica tu razonamiento de forma estructurada.',
              min_words: 8,
              keywords_expected: rubricWords
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean),
            }
          : {
              card_title: prompt.slice(0, 90),
              visual_caption: explanation.slice(0, 160),
              key_points: [correctOpt, explanation],
              check_question: {
                question: prompt,
                options: [
                  { id: 'a', text: correctOpt },
                  { id: 'b', text: wrongOpt },
                ],
              },
            };
      const answer_key_json =
        itemType === 'open_response'
          ? {
              reference_answer: correctOpt,
              rubric_criteria: rubricWords
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean),
              auto_ai_grade: true,
            }
          : { correct_option_id: 'a' };

      return apiRequest<QuestionBankOut>(`${prefix}/question-bank`, {
        method: 'POST',
        body: JSON.stringify({
          topic_tag: topicTag.trim() || 'general',
          challenge_type: itemType,
          schema_version: 1,
          prompt,
          payload_json,
          answer_key_json,
          pedagogical_explanation: explanation,
          difficulty: 2,
          points,
          estimated_seconds: itemType === 'open_response' ? 90 : 30,
          is_safety_critical: false,
        }),
      });
    },
    onSuccess: (created) => {
      setPrompt('');
      setFeedback(`Pregunta agregada al banco bajo la etiqueta "${created.topic_tag}".`);
      void queryClient.invalidateQueries({ queryKey: ['studio-question-bank', prefix] });
    },
  });

  const deleteBankItem = useMutation({
    mutationFn: (id: string) => apiRequest<void>(`${prefix}/question-bank/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      setFeedback('Reactivo eliminado del banco.');
      void queryClient.invalidateQueries({ queryKey: ['studio-question-bank', prefix] });
    },
  });

  const pullToVersion = useMutation({
    mutationFn: () =>
      apiRequest<unknown[]>(`${prefix}/lesson-versions/${selectedLessonVersionId}/pull-from-bank`, {
        method: 'POST',
        body: JSON.stringify({
          count: pullCount,
          topic_tag: pullTopic.trim() || null,
        }),
      }),
    onSuccess: (created) => {
      setFeedback(`Se inyectaron ${created.length} pregunta(s) del banco en la versión activa.`);
      void queryClient.invalidateQueries({ queryKey: ['studio-challenges', prefix, selectedLessonVersionId] });
    },
  });

  const gradeSubmission = useMutation({
    mutationFn: ({ subId, score, teacherNote }: { subId: string; score: number; teacherNote: string }) =>
      apiRequest<OpenSubmissionOut>(`${prefix}/open-submissions/${subId}/grade`, {
        method: 'PATCH',
        body: JSON.stringify({ final_score: score, teacher_feedback: teacherNote }),
      }),
    onSuccess: (updated) => {
      setFeedback(`Entrega calificada con ${updated.final_score}/${updated.max_points} pts.`);
      void queryClient.invalidateQueries({ queryKey: ['studio-open-submissions', prefix] });
    },
  });

  const err =
    createBankItem.error || deleteBankItem.error || pullToVersion.error || gradeSubmission.error;

  return (
    <div className="space-y-6">
      {feedback && <SuccessBanner message={feedback} />}
      {err && <ErrorBanner message={(err as Error).message} />}

      {/* Banco de preguntas */}
      <div className="grid gap-5 lg:grid-cols-2">
        <form onSubmit={createBankItem.mutate} className="surface-card p-5 space-y-3">
          <h2 className="flex items-center gap-2 text-base font-bold">
            <Database className="h-5 w-5 text-[var(--brand-primary)]" /> Banco Reutilizable de Preguntas
          </h2>
          <div className="grid gap-2 sm:grid-cols-3">
            <input
              placeholder="Etiqueta / Tema"
              value={topicTag}
              onChange={(e) => setTopicTag(e.target.value)}
              className="rounded-lg border border-[var(--border-subtle)] px-2.5 py-1.5 text-xs"
            />
            <select
              value={itemType}
              onChange={(e) => setItemType(e.target.value as typeof itemType)}
              className="rounded-lg border border-[var(--border-subtle)] bg-white px-2.5 py-1.5 text-xs font-semibold"
            >
              <option value="visual_concept_card">Opción / Tarjeta</option>
              <option value="open_response">Respuesta Abierta (Rúbrica IA)</option>
            </select>
            <input
              type="number"
              min={5}
              max={200}
              value={points}
              onChange={(e) => setPoints(Number(e.target.value))}
              className="rounded-lg border border-[var(--border-subtle)] px-2.5 py-1.5 text-xs"
            />
          </div>
          <input
            required
            minLength={3}
            placeholder="Pregunta o consigna del banco..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
          />
          {itemType === 'open_response' ? (
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                placeholder="Respuesta modelo de referencia"
                value={correctOpt}
                onChange={(e) => setCorrectOpt(e.target.value)}
                className="rounded-lg border border-[var(--border-subtle)] px-2.5 py-1.5 text-xs"
              />
              <input
                placeholder="Palabras clave rúbrica (coma separada)"
                value={rubricWords}
                onChange={(e) => setRubricWords(e.target.value)}
                className="rounded-lg border border-[var(--border-subtle)] px-2.5 py-1.5 text-xs"
              />
            </div>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                placeholder="Opción correcta"
                value={correctOpt}
                onChange={(e) => setCorrectOpt(e.target.value)}
                className="rounded-lg border border-[var(--border-subtle)] px-2.5 py-1.5 text-xs"
              />
              <input
                placeholder="Distractor"
                value={wrongOpt}
                onChange={(e) => setWrongOpt(e.target.value)}
                className="rounded-lg border border-[var(--border-subtle)] px-2.5 py-1.5 text-xs"
              />
            </div>
          )}
          <input
            placeholder="Explicación pedagógica..."
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
            className="w-full rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs"
          />
          <button type="submit" disabled={createBankItem.isPending} className="btn-primary inline-flex items-center gap-1 px-4 py-2 text-xs font-bold">
            <Plus className="h-3.5 w-3.5" /> Guardar en Banco
          </button>
        </form>

        <div className="surface-card p-5 space-y-3">
          <h3 className="flex items-center gap-2 text-base font-bold">
            <Shuffle className="h-5 w-5 text-[var(--brand-primary)]" /> Inyectar Preguntas Aleatorias en Examen
          </h3>
          <p className="text-xs text-[var(--text-secondary)]">
            Extrae reactivos del banco hacia la versión activa (selecciona un nodo en la pestaña "Retos y Pruebas Fuertes").
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            <input
              type="number"
              min={1}
              max={30}
              value={pullCount}
              onChange={(e) => setPullCount(Number(e.target.value))}
              className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-xs"
            />
            <input
              placeholder="Filtrar tema (opcional)"
              value={pullTopic}
              onChange={(e) => setPullTopic(e.target.value)}
              className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-xs"
            />
          </div>
          <button
            type="button"
            disabled={!selectedLessonVersionId || pullToVersion.isPending}
            onClick={() => pullToVersion.mutate()}
            className="btn-primary w-full py-2 text-xs font-bold disabled:opacity-50"
          >
            {selectedLessonVersionId
              ? 'Insertar desde Banco en Versión Activa'
              : 'Primero elige una versión en Retos y Pruebas Fuertes'}
          </button>

          <div className="max-h-48 space-y-2 overflow-y-auto pt-2">
            {(bankQuery.data ?? []).map((item) => (
              <div key={item.id} className="flex items-start justify-between gap-2 rounded-lg border border-[var(--border-subtle)] bg-slate-50 p-2.5 text-xs">
                <div>
                  <p className="font-semibold">{item.prompt}</p>
                  <p className="text-[11px] text-[var(--text-secondary)]">
                    #{item.topic_tag} • {item.challenge_type} • {item.points} pts
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => deleteBankItem.mutate(item.id)}
                  className="text-slate-400 hover:text-rose-600"
                  aria-label="Eliminar del banco"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bandeja de calificación de respuestas abiertas */}
      <section className="surface-card p-5 space-y-3">
        <h2 className="flex items-center gap-2 text-base font-bold">
          <CheckSquare className="h-5 w-5 text-[var(--brand-primary)]" /> Revisión Docente de Respuestas Abiertas
        </h2>
        {submissionsQuery.isLoading ? (
          <LoadingState label="Cargando respuestas abiertas..." />
        ) : !submissionsQuery.data?.length ? (
          <EmptyState
            title="Sin respuestas abiertas pendientes"
            description="Cuando los estudiantes envíen retos de tipo Respuesta Abierta aparecerán aquí con su pre-evaluación IA."
          />
        ) : (
          <div className="space-y-3">
            {submissionsQuery.data.map((sub) => {
              const currentScore = scoresMap[sub.id] ?? sub.final_score ?? sub.ai_suggested_score ?? 0;
              const currentNote = notesMap[sub.id] ?? sub.teacher_feedback ?? '';
              return (
                <div key={sub.id} className="rounded-xl border border-[var(--border-subtle)] bg-white p-4 space-y-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-bold text-[var(--brand-primary)]">
                      Estado: {sub.status} • Pre-nota IA: {sub.ai_suggested_score ?? '-'} / {sub.max_points} pts
                    </span>
                    {sub.ai_feedback && (
                      <span className="text-[11px] text-[var(--text-secondary)]">IA: {sub.ai_feedback}</span>
                    )}
                  </div>
                  <p className="rounded-lg bg-slate-50 p-3 text-sm">{sub.response_text}</p>
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      type="number"
                      min={0}
                      max={sub.max_points}
                      value={currentScore}
                      onChange={(e) =>
                        setScoresMap((prev) => ({ ...prev, [sub.id]: Number(e.target.value) }))
                      }
                      className="w-20 rounded-lg border border-[var(--border-subtle)] px-2.5 py-1.5 text-xs"
                    />
                    <input
                      placeholder="Retroalimentación del docente..."
                      value={currentNote}
                      onChange={(e) =>
                        setNotesMap((prev) => ({ ...prev, [sub.id]: e.target.value }))
                      }
                      className="flex-1 min-w-[200px] rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs"
                    />
                    <button
                      type="button"
                      disabled={gradeSubmission.isPending}
                      onClick={() =>
                        gradeSubmission.mutate({
                          subId: sub.id,
                          score: currentScore,
                          teacherNote: currentNote,
                        })
                      }
                      className="btn-primary px-4 py-1.5 text-xs font-semibold"
                    >
                      Aprobar Calificación
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
