import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, Download, Edit3, Flame, Play, Plus, Radio, Sparkles, Trash2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { EmptyState, ErrorBanner, LoadingState, SuccessBanner } from '../ui/StatusStates';
import { apiRequest, downloadAuthenticatedBlob } from '../../services/apiClient';
import { VisualZoneEditor, type EditableZone } from './VisualZoneEditor';
import type {
  ChallengeAuthorOut,
  ChallengeType,
  CourseDetail,
  CourseSummary,
  GenerateLessonDraftResponse,
  LessonVersionOut,
  LiveSessionStateOut,
  MediaAssetOut,
} from '../../types/api';
import { scopePrefix, type StudioScope } from './studioHelpers';

interface Props {
  scope: StudioScope;
  selectedCourseId: string;
  selectedLessonId: string;
  onSelectCourse: (id: string) => void;
  onSelectLesson: (id: string) => void;
  onVersionSelected: (lvId: string) => void;
}

export function ChallengesExamTab({
  scope,
  selectedCourseId,
  selectedLessonId,
  onSelectCourse,
  onSelectLesson,
  onVersionSelected,
}: Props) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const prefix = scopePrefix(scope);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [selectedLvId, setSelectedLvId] = useState('');
  const [customZones, setCustomZones] = useState<EditableZone[]>([]);
  const [correctZoneId, setCorrectZoneId] = useState('');

  // IA generators
  const [sourceText, setSourceText] = useState('');
  const [examDifficulty, setExamDifficulty] = useState(4);
  const [examCount, setExamCount] = useState(6);

  // Manual challenge form
  const [chType, setChType] = useState<ChallengeType>('visual_concept_card');
  const [chPrompt, setChPrompt] = useState('');
  const [chExplanation, setChExplanation] = useState('');
  const [chPoints, setChPoints] = useState(15);
  const [chDifficulty, setChDifficulty] = useState(2);
  const [chSafety, setChSafety] = useState(false);
  const [attachedMediaId, setAttachedMediaId] = useState('');

  // Manual type-specific helpers
  const [optCorrect, setOptCorrect] = useState('');
  const [optWrong, setOptWrong] = useState('');
  const [seqLines, setSeqLines] = useState('Paso inicial\nSegundo paso\nPaso de cierre');
  const [pairLines, setPairLines] = useState('Concepto A | Definición A\nConcepto B | Definición B');
  const [blankTemplate, setBlankTemplate] = useState('Para dominar el tema se aplica {{b1}} seguido de {{b2}}.');
  const [blankB1, setBlankB1] = useState('análisis previo');
  const [blankB2, setBlankB2] = useState('verificación');

  // Inline edit challenge
  const [editingCh, setEditingCh] = useState<ChallengeAuthorOut | null>(null);

  const coursesQuery = useQuery({
    queryKey: ['studio-courses', prefix],
    queryFn: () => apiRequest<CourseSummary[]>(`${prefix}/courses`),
  });
  const activeCourseId = selectedCourseId || coursesQuery.data?.[0]?.id || '';

  const detailQuery = useQuery({
    queryKey: ['studio-course-detail', activeCourseId],
    queryFn: () => apiRequest<CourseDetail>(`/courses/${activeCourseId}`),
    enabled: Boolean(activeCourseId),
  });
  const allLessons = (detailQuery.data?.modules ?? []).flatMap((m) => m.lessons);
  const activeLessonId = selectedLessonId || allLessons[0]?.id || '';

  const versionsQuery = useQuery({
    queryKey: ['studio-versions', prefix, activeLessonId],
    queryFn: () => apiRequest<LessonVersionOut[]>(`${prefix}/lessons/${activeLessonId}/versions`),
    enabled: Boolean(activeLessonId),
  });
  const activeLvId = selectedLvId || versionsQuery.data?.[0]?.id || '';
  const activeLv = versionsQuery.data?.find((v) => v.id === activeLvId);

  const challengesQuery = useQuery({
    queryKey: ['studio-challenges', prefix, activeLvId],
    queryFn: () => apiRequest<ChallengeAuthorOut[]>(`${prefix}/lesson-versions/${activeLvId}/challenges`),
    enabled: Boolean(activeLvId),
  });

  const mediaQuery = useQuery({
    queryKey: ['studio-media', prefix],
    queryFn: () => apiRequest<MediaAssetOut[]>(`${prefix}/media`),
  });

  const createDraftVersion = useMutation({
    mutationFn: () =>
      apiRequest<LessonVersionOut>(`${prefix}/lessons/${activeLessonId}/versions`, {
        method: 'POST',
        body: JSON.stringify({ summary: 'Nuevo borrador de edición', requires_revalidation: false }),
      }),
    onSuccess: (lv) => {
      setSelectedLvId(lv.id);
      onVersionSelected(lv.id);
      setFeedback(`Borrador v${lv.version_number} creado.`);
      void queryClient.invalidateQueries({ queryKey: ['studio-versions', prefix, activeLessonId] });
    },
  });

  const generateDraftAI = useMutation({
    mutationFn: () =>
      apiRequest<GenerateLessonDraftResponse>(`${prefix}/ai/generate-lesson-draft`, {
        method: 'POST',
        body: JSON.stringify({ lesson_version_id: activeLvId, source_text: sourceText }),
      }),
    onSuccess: (res) => {
      setSourceText('');
      setFeedback(`Lección IA generada (${res.challenges_created} retos vía ${res.provider}).`);
      void queryClient.invalidateQueries({ queryKey: ['studio-challenges', prefix, activeLvId] });
    },
  });

  const generateStrongExamAI = useMutation({
    mutationFn: () =>
      apiRequest<GenerateLessonDraftResponse>(`${prefix}/ai/generate-strong-exam`, {
        method: 'POST',
        body: JSON.stringify({
          lesson_version_id: activeLvId,
          source_text: sourceText,
          difficulty_target: examDifficulty,
          question_count: examCount,
        }),
      }),
    onSuccess: (res) => {
      setSourceText('');
      setFeedback(`Prueba Fuerte IA generada (${res.challenges_created} retos exigentes vía ${res.provider}).`);
      void queryClient.invalidateQueries({ queryKey: ['studio-challenges', prefix, activeLvId] });
      void queryClient.invalidateQueries({ queryKey: ['studio-course-detail', activeCourseId] });
    },
  });

  const buildManualBody = () => {
    const nextIdx = (challengesQuery.data?.length ?? 0) + 1;
    let payload_json: Record<string, unknown> = {};
    let answer_key_json: Record<string, unknown> = {};

    if (chType === 'visual_concept_card') {
      payload_json = {
        card_title: chPrompt.slice(0, 100),
        visual_media_id: attachedMediaId || null,
        visual_caption: chExplanation.slice(0, 200),
        key_points: [optCorrect || chPrompt, chExplanation],
        check_question: {
          question: chPrompt,
          options: [
            { id: 'a', text: optCorrect || 'Opción correcta' },
            { id: 'b', text: optWrong || 'Distractor frecuente' },
          ],
        },
      };
      answer_key_json = { correct_option_id: 'a' };
    } else if (chType === 'sequence_ordering') {
      const steps = seqLines
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean)
        .map((text, idx) => ({ id: `s${idx + 1}`, text }));
      payload_json = { instruction: 'Ordena los pasos del primero al último.', items: steps };
      answer_key_json = { expected_order: steps.map((s) => s.id) };
    } else if (chType === 'matching') {
      const rows = pairLines
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean)
        .map((l, idx) => {
          const [left, right] = l.split('|').map((x) => x.trim());
          return { lid: `l${idx + 1}`, left: left || `Ítem ${idx + 1}`, rid: `r${idx + 1}`, right: right || 'Par' };
        });
      payload_json = {
        instruction: 'Relaciona cada concepto con su correspondencia exacta.',
        left_items: rows.map((r) => ({ id: r.lid, text: r.left })),
        right_items: rows.map((r) => ({ id: r.rid, text: r.right })),
        shuffle: true,
      };
      answer_key_json = { pairs: Object.fromEntries(rows.map((r) => [r.lid, r.rid])) };
    } else if (chType === 'fill_in_blanks') {
      payload_json = {
        template: blankTemplate,
        input_mode: 'word_bank',
        word_bank: [blankB1, blankB2, 'distractor'],
        blanks: [
          { id: 'b1', label: 'Espacio 1' },
          { id: 'b2', label: 'Espacio 2' },
        ],
      };
      answer_key_json = {
        blanks: {
          b1: { accepted: [blankB1], case_sensitive: false },
          b2: { accepted: [blankB2], case_sensitive: false },
        },
      };
    } else if (chType === 'decision_simulation') {
      payload_json = {
        scenario_context: chPrompt,
        initial_node_id: 'n1',
        nodes: {
          n1: {
            narrative: '¿Qué decisión tomas ante este escenario?',
            choices: [
              { id: 'c_ok', text: optCorrect || 'Ejecutar acción segura y verificada', next_node_id: 'end_ok' },
              { id: 'c_err', text: optWrong || 'Saltar validación inicial', next_node_id: 'end_bad' },
            ],
          },
          end_ok: { is_terminal: true, summary: 'Resolución correcta del escenario.' },
          end_bad: { is_terminal: true, summary: 'Error de criterio.' },
        },
      };
      answer_key_json = { optimal_paths: [['c_ok']], acceptable_terminal_nodes: ['end_ok'] };
    } else {
      // interactive_zones
      const selectedMedia = mediaQuery.data?.find((m) => m.id === attachedMediaId);
      const specZones = (selectedMedia?.dynamic_spec_json as { zones?: Record<string, unknown>[] } | null)?.zones;
      const zones =
        customZones.length >= 2
          ? customZones
          : specZones && specZones.length >= 2
            ? specZones
            : [
                { id: 'z1', shape: 'circle', x: 0.35, y: 0.45, r: 0.1, label: optCorrect || 'Zona correcta' },
                { id: 'z2', shape: 'circle', x: 0.7, y: 0.45, r: 0.1, label: optWrong || 'Zona alternativa' },
              ];
      const firstId =
        customZones.length >= 2 && correctZoneId
          ? correctZoneId
          : String((zones[0] as { id?: string }).id || 'z1');
      payload_json = {
        instruction: 'Selecciona la zona correspondiente en el esquema.',
        diagram_media_id: attachedMediaId || null,
        aspect_ratio: '16:9',
        selection_mode: 'single',
        zones,
      };
      answer_key_json = { correct_zone_ids: [firstId], accept_coordinates_within_zones: true };
    }

    return {
      challenge_type: chType,
      schema_version: 1,
      order_index: nextIdx,
      prompt: chPrompt,
      payload_json,
      answer_key_json,
      pedagogical_explanation: chExplanation,
      difficulty: chDifficulty,
      points: chPoints,
      estimated_seconds: 45,
      is_safety_critical: chSafety,
    };
  };

  const createManualChallenge = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      return apiRequest<ChallengeAuthorOut>(`${prefix}/lesson-versions/${activeLvId}/challenges`, {
        method: 'POST',
        body: JSON.stringify(buildManualBody()),
      });
    },
    onSuccess: () => {
      setChPrompt('');
      setChExplanation('');
      setFeedback('Reto creado manualmente.');
      void queryClient.invalidateQueries({ queryKey: ['studio-challenges', prefix, activeLvId] });
    },
  });

  const updateChallenge = useMutation({
    mutationFn: (ch: ChallengeAuthorOut) =>
      apiRequest<ChallengeAuthorOut>(`${prefix}/challenges/${ch.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          prompt: ch.prompt,
          pedagogical_explanation: ch.pedagogical_explanation,
          points: ch.points,
          difficulty: ch.difficulty,
        }),
      }),
    onSuccess: () => {
      setEditingCh(null);
      setFeedback('Reto actualizado.');
      void queryClient.invalidateQueries({ queryKey: ['studio-challenges', prefix, activeLvId] });
    },
  });

  const deleteChallenge = useMutation({
    mutationFn: (id: string) => apiRequest<void>(`${prefix}/challenges/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      setFeedback('Reto eliminado.');
      void queryClient.invalidateQueries({ queryKey: ['studio-challenges', prefix, activeLvId] });
    },
  });

  const publishVersion = useMutation({
    mutationFn: () =>
      apiRequest<LessonVersionOut>(`${prefix}/lesson-versions/${activeLvId}/publish`, { method: 'POST' }),
    onSuccess: () => {
      setFeedback('Versión aprobada y publicada para estudiantes.');
      void queryClient.invalidateQueries({ queryKey: ['studio-versions', prefix, activeLessonId] });
      void queryClient.invalidateQueries({ queryKey: ['studio-course-detail', activeCourseId] });
    },
  });

  const launchLiveMutation = useMutation({
    mutationFn: () =>
      apiRequest<LiveSessionStateOut>(`${prefix}/live-sessions`, {
        method: 'POST',
        body: JSON.stringify({
          lesson_version_id: activeLvId,
          title: allLessons.find((l) => l.id === activeLessonId)?.title || 'Clase en Vivo Vistazo',
        }),
      }),
    onSuccess: (room) => {
      navigate(`/vivo/${room.room_code}?host=1`);
    },
  });

  const err =
    createDraftVersion.error ||
    generateDraftAI.error ||
    generateStrongExamAI.error ||
    createManualChallenge.error ||
    updateChallenge.error ||
    deleteChallenge.error ||
    publishVersion.error;

  return (
    <div className="space-y-5">
      {feedback && <SuccessBanner message={feedback} />}
      {err && <ErrorBanner message={(err as Error).message} />}

      {/* Selector Curso -> Nodo -> Versión */}
      <section className="surface-card p-5 space-y-3">
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-xs font-semibold">
            Materia / Curso
            <select
              value={activeCourseId}
              onChange={(e) => {
                onSelectCourse(e.target.value);
                onSelectLesson('');
                setSelectedLvId('');
              }}
              className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] bg-white px-2.5 py-2 text-sm"
            >
              {(coursesQuery.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold">
            Nodo / Lección
            <select
              value={activeLessonId}
              onChange={(e) => {
                onSelectLesson(e.target.value);
                setSelectedLvId('');
              }}
              className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] bg-white px-2.5 py-2 text-sm"
            >
              {allLessons.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.title} ({l.lesson_type ?? 'micro_lesson'})
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold">
            Versión
            <div className="mt-1 flex gap-2">
              <select
                value={activeLvId}
                onChange={(e) => {
                  setSelectedLvId(e.target.value);
                  onVersionSelected(e.target.value);
                }}
                className="flex-1 rounded-lg border border-[var(--border-subtle)] bg-white px-2.5 py-2 text-sm"
              >
                {(versionsQuery.data ?? []).map((v) => (
                  <option key={v.id} value={v.id}>
                    v{v.version_number} ({v.status})
                  </option>
                ))}
              </select>
              {activeLessonId && (
                <button
                  type="button"
                  onClick={() => createDraftVersion.mutate()}
                  className="rounded-lg border border-[var(--border-subtle)] px-2.5 text-xs font-semibold hover:bg-slate-50"
                >
                  + Draft
                </button>
              )}
            </div>
          </label>
        </div>

        {activeLv && (
          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[var(--border-subtle)]">
            <span className="text-xs">
              Estado: <strong className="uppercase">{activeLv.status}</strong> •{' '}
              {challengesQuery.data?.length ?? 0} retos cargados
            </span>
            <div className="flex flex-wrap gap-2">
              {Boolean(challengesQuery.data?.length) && (
                <>
                  <button
                    type="button"
                    onClick={() =>
                      void downloadAuthenticatedBlob(
                        `${prefix}/lesson-versions/${activeLv.id}/exam-pdf?include_answers=false`,
                        `evaluacion-${activeLv.id}.pdf`
                      )
                    }
                    className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs font-semibold hover:bg-slate-50"
                  >
                    <Download className="h-3.5 w-3.5" /> PDF Alumno
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      void downloadAuthenticatedBlob(
                        `${prefix}/lesson-versions/${activeLv.id}/exam-pdf?include_answers=true`,
                        `evaluacion-clave-${activeLv.id}.pdf`
                      )
                    }
                    className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs font-semibold hover:bg-slate-50"
                  >
                    <Download className="h-3.5 w-3.5" /> PDF + Clave
                  </button>
                  <button
                    type="button"
                    disabled={launchLiveMutation.isPending}
                    onClick={() => launchLiveMutation.mutate()}
                    className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-indigo-700"
                  >
                    <Radio className="h-3.5 w-3.5" /> Lanzar Clase en Vivo
                  </button>
                </>
              )}
              {activeLv.status === 'published' && (
                <Link
                  to={`/lessons/${activeLv.id}`}
                  className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs font-semibold hover:bg-slate-50"
                >
                  <Play className="h-3.5 w-3.5" /> Probar como alumno
                </Link>
              )}
              {activeLv.status === 'draft' && (
                <button
                  type="button"
                  disabled={publishVersion.isPending || !(challengesQuery.data?.length)}
                  onClick={() => publishVersion.mutate()}
                  className="btn-primary inline-flex items-center gap-1 px-4 py-1.5 text-xs font-bold disabled:opacity-50"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" /> Aprobar y Publicar
                </button>
              )}
            </div>
          </div>
        )}
      </section>

      {activeLv && (
        <div className="grid gap-5 lg:grid-cols-2">
          {/* Asistente IA: Lección o Prueba Fuerte */}
          <section className="surface-card p-5 space-y-3">
            <h2 className="flex items-center gap-2 text-base font-bold">
              <Sparkles className="h-5 w-5 text-[var(--brand-primary)]" /> Generador IA: Lección o Prueba Fuerte
            </h2>
            {activeLv.status !== 'draft' ? (
              <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">
                Esta versión está <strong>{activeLv.status}</strong>. Haz clic en <strong>+ Draft</strong> arriba para generar nuevos retos IA sin alterar la versión publicada.
              </p>
            ) : (
              <>
                <textarea
                  rows={5}
                  placeholder="Pega contenido, protocolo o guía (mín. 80 chars para Lección, 40 chars para Prueba Fuerte)..."
                  value={sourceText}
                  onChange={(e) => setSourceText(e.target.value)}
                  className="w-full rounded-lg border border-[var(--border-subtle)] p-3 text-sm"
                />
                <div className="grid gap-2 sm:grid-cols-2 text-xs">
                  <label className="font-semibold">
                    Rigurosidad Prueba Fuerte (3-5)
                    <input
                      type="number"
                      min={3}
                      max={5}
                      value={examDifficulty}
                      onChange={(e) => setExamDifficulty(Number(e.target.value))}
                      className="mt-1 w-full rounded border px-2 py-1"
                    />
                  </label>
                  <label className="font-semibold">
                    Cantidad retos prueba (5-8)
                    <input
                      type="number"
                      min={5}
                      max={8}
                      value={examCount}
                      onChange={(e) => setExamCount(Number(e.target.value))}
                      className="mt-1 w-full rounded border px-2 py-1"
                    />
                  </label>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={generateDraftAI.isPending || sourceText.trim().length < 80}
                    onClick={() => generateDraftAI.mutate()}
                    className="btn-primary flex-1 py-2 text-xs font-semibold disabled:opacity-50"
                  >
                    {generateDraftAI.isPending ? 'Generando...' : 'Generar Microlección IA'}
                  </button>
                  <button
                    type="button"
                    disabled={generateStrongExamAI.isPending || sourceText.trim().length < 40}
                    onClick={() => generateStrongExamAI.mutate()}
                    className="inline-flex flex-1 items-center justify-center gap-1 rounded-lg bg-amber-600 px-3 py-2 text-xs font-bold text-white hover:bg-amber-700 disabled:opacity-50"
                  >
                    <Flame className="h-3.5 w-3.5" />
                    {generateStrongExamAI.isPending ? 'Generando...' : 'Generar Prueba Fuerte IA'}
                  </button>
                </div>
              </>
            )}
          </section>

          {/* Constructor Manual de los 6 tipos de reto */}
          <form onSubmit={createManualChallenge.mutate} className="surface-card p-5 space-y-3">
            <h2 className="flex items-center gap-2 text-base font-bold">
              <Plus className="h-5 w-5 text-[var(--brand-primary)]" /> Agregar Reto Manualmente
            </h2>
            <div className="grid gap-2 sm:grid-cols-2">
              <select
                value={chType}
                onChange={(e) => setChType(e.target.value as ChallengeType)}
                className="rounded-lg border border-[var(--border-subtle)] bg-white px-2.5 py-2 text-xs font-semibold"
              >
                <option value="visual_concept_card">Tarjeta Conceptual Visual</option>
                <option value="matching">Emparejamiento</option>
                <option value="sequence_ordering">Ordenar Secuencia</option>
                <option value="interactive_zones">Zonas Interactivas (Diagrama)</option>
                <option value="decision_simulation">Simulación de Decisiones</option>
                <option value="fill_in_blanks">Completar Espacios</option>
              </select>
              <select
                value={attachedMediaId}
                onChange={(e) => setAttachedMediaId(e.target.value)}
                className="rounded-lg border border-[var(--border-subtle)] bg-white px-2.5 py-2 text-xs"
              >
                <option value="">Sin imagen dinámica adjunta</option>
                {(mediaQuery.data ?? []).map((m) => (
                  <option key={m.id} value={m.id}>
                    Visual: {m.title}
                  </option>
                ))}
              </select>
            </div>

            <input
              required
              minLength={3}
              placeholder="Consigna o pregunta principal del reto..."
              value={chPrompt}
              onChange={(e) => setChPrompt(e.target.value)}
              className="w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
            />

            {(chType === 'visual_concept_card' || chType === 'decision_simulation') && (
              <div className="grid gap-2 sm:grid-cols-2">
                <input
                  placeholder="Respuesta / opción correcta"
                  value={optCorrect}
                  onChange={(e) => setOptCorrect(e.target.value)}
                  className="rounded-lg border border-[var(--border-subtle)] px-2.5 py-1.5 text-xs"
                />
                <input
                  placeholder="Opción distractora"
                  value={optWrong}
                  onChange={(e) => setOptWrong(e.target.value)}
                  className="rounded-lg border border-[var(--border-subtle)] px-2.5 py-1.5 text-xs"
                />
              </div>
            )}

            {chType === 'interactive_zones' && (
              <VisualZoneEditor
                imageUrl={mediaQuery.data?.find((m) => m.id === attachedMediaId)?.signed_url}
                zones={customZones}
                correctZoneId={correctZoneId}
                onChangeZones={setCustomZones}
                onChangeCorrectZoneId={setCorrectZoneId}
              />
            )}

            {chType === 'sequence_ordering' && (
              <textarea
                rows={3}
                value={seqLines}
                onChange={(e) => setSeqLines(e.target.value)}
                placeholder="Un paso por línea en orden correcto..."
                className="w-full rounded-lg border p-2 text-xs"
              />
            )}

            {chType === 'matching' && (
              <textarea
                rows={3}
                value={pairLines}
                onChange={(e) => setPairLines(e.target.value)}
                placeholder="Concepto | Par (uno por línea)"
                className="w-full rounded-lg border p-2 text-xs"
              />
            )}

            {chType === 'fill_in_blanks' && (
              <div className="space-y-1.5">
                <input
                  value={blankTemplate}
                  onChange={(e) => setBlankTemplate(e.target.value)}
                  className="w-full rounded-lg border px-2.5 py-1.5 text-xs"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    value={blankB1}
                    onChange={(e) => setBlankB1(e.target.value)}
                    placeholder="Respuesta {{b1}}"
                    className="rounded border px-2 py-1 text-xs"
                  />
                  <input
                    value={blankB2}
                    onChange={(e) => setBlankB2(e.target.value)}
                    placeholder="Respuesta {{b2}}"
                    className="rounded border px-2 py-1 text-xs"
                  />
                </div>
              </div>
            )}

            <textarea
              required
              minLength={5}
              rows={2}
              placeholder="Explicación pedagógica verificable tras responder..."
              value={chExplanation}
              onChange={(e) => setChExplanation(e.target.value)}
              className="w-full rounded-lg border border-[var(--border-subtle)] p-2.5 text-xs"
            />

            <div className="flex flex-wrap items-center gap-3 text-xs">
              <label className="flex items-center gap-1">
                Puntos:
                <input
                  type="number"
                  min={1}
                  max={500}
                  value={chPoints}
                  onChange={(e) => setChPoints(Number(e.target.value))}
                  className="w-16 rounded border px-1.5 py-1"
                />
              </label>
              <label className="flex items-center gap-1">
                Dificultad (1-5):
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={chDifficulty}
                  onChange={(e) => setChDifficulty(Number(e.target.value))}
                  className="w-14 rounded border px-1.5 py-1"
                />
              </label>
              <label className="flex items-center gap-1.5">
                <input type="checkbox" checked={chSafety} onChange={(e) => setChSafety(e.target.checked)} />
                Seguridad crítica
              </label>
            </div>

            <button type="submit" disabled={createManualChallenge.isPending} className="btn-primary w-full py-2 text-xs font-semibold">
              Guardar Reto Manual
            </button>
          </form>
        </div>
      )}

      {/* Listado CRUD de retos en la versión */}
      {activeLvId && (
        <section className="surface-card p-5 space-y-3">
          <h3 className="text-sm font-bold uppercase text-[var(--text-secondary)]">
            Retos en esta versión ({challengesQuery.data?.length ?? 0})
          </h3>
          {challengesQuery.isLoading ? (
            <LoadingState label="Cargando retos..." />
          ) : !challengesQuery.data?.length ? (
            <EmptyState title="Sin retos aún" description="Crea retos manualmente o usa el Generador IA arriba." />
          ) : (
            <ul className="space-y-2">
              {challengesQuery.data.map((ch, idx) => (
                <li key={ch.id} className="rounded-xl border border-[var(--border-subtle)] bg-white p-3.5 text-xs space-y-1.5">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="font-bold text-[var(--brand-primary)]">
                        #{idx + 1} [{ch.challenge_type}] • Dificultad {ch.difficulty}/5 • {ch.points} pts • {ch.status}
                      </span>
                      <p className="mt-1 text-sm font-semibold">{ch.prompt}</p>
                    </div>
                    <div className="flex gap-1">
                      <button
                        type="button"
                        onClick={() => setEditingCh(ch)}
                        className="rounded border p-1.5 hover:bg-slate-50"
                        aria-label="Editar reto"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteChallenge.mutate(ch.id)}
                        className="rounded border border-red-200 p-1.5 text-red-700 hover:bg-red-50"
                        aria-label="Eliminar reto"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  <p className="text-[var(--text-secondary)]">{ch.pedagogical_explanation}</p>
                </li>
              ))}
            </ul>
          )}

          {editingCh && (
            <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 space-y-2">
              <p className="text-xs font-bold text-amber-950">Editar reto</p>
              <input
                value={editingCh.prompt}
                onChange={(e) => setEditingCh({ ...editingCh, prompt: e.target.value })}
                className="w-full rounded border border-amber-300 bg-white px-2.5 py-1.5 text-sm"
              />
              <textarea
                rows={2}
                value={editingCh.pedagogical_explanation}
                onChange={(e) => setEditingCh({ ...editingCh, pedagogical_explanation: e.target.value })}
                className="w-full rounded border border-amber-300 bg-white p-2 text-xs"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => updateChallenge.mutate(editingCh)}
                  className="btn-primary px-3 py-1.5 text-xs font-semibold"
                >
                  Guardar cambios
                </button>
                <button
                  type="button"
                  onClick={() => setEditingCh(null)}
                  className="rounded border bg-white px-3 py-1.5 text-xs font-semibold"
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
