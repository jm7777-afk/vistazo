import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowDown, ArrowUp, CheckCircle2, ShieldAlert } from 'lucide-react';
import { apiRequest, resolveAssetUrl } from '../../services/apiClient';
import type { ChallengePublic } from '../../types/api';
import { DictationButton, SpeakButton } from './VoiceControls';

function useSignedMediaUrl(mediaId?: string | null) {
  const query = useQuery({
    queryKey: ['signed-media', mediaId],
    queryFn: () => apiRequest<{ signed_url: string }>(`/media/${mediaId}/signed-url`),
    enabled: Boolean(mediaId),
    staleTime: 60_000,
  });
  return query.data ? resolveAssetUrl(query.data.signed_url) : null;
}

interface Props {
  challenge: ChallengePublic;
  disabled: boolean;
  onSubmit: (answer: Record<string, unknown>) => void;
}

export function ChallengeRenderer({ challenge, disabled, onSubmit }: Props) {
  switch (challenge.challenge_type) {
    case 'visual_concept_card':
      return <VisualConceptCardView challenge={challenge} disabled={disabled} onSubmit={onSubmit} />;
    case 'matching':
      return <MatchingView challenge={challenge} disabled={disabled} onSubmit={onSubmit} />;
    case 'sequence_ordering':
      return <SequenceOrderingView challenge={challenge} disabled={disabled} onSubmit={onSubmit} />;
    case 'interactive_zones':
      return <InteractiveZonesView challenge={challenge} disabled={disabled} onSubmit={onSubmit} />;
    case 'decision_simulation':
      return <DecisionSimulationView challenge={challenge} disabled={disabled} onSubmit={onSubmit} />;
    case 'fill_in_blanks':
      return <FillInBlanksView challenge={challenge} disabled={disabled} onSubmit={onSubmit} />;
    case 'open_response':
      return <OpenResponseView challenge={challenge} disabled={disabled} onSubmit={onSubmit} />;
    default:
      return <p className="text-sm text-red-600">Tipo de reto no soportado.</p>;
  }
}

function ChallengeHeader({ challenge }: { challenge: ChallengePublic }) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-[var(--bg-accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--brand-primary)]">
          {challenge.challenge_type.replace(/_/g, ' ')} • {challenge.points} pts
        </span>
        <SpeakButton text={challenge.prompt} />
      </div>
      {challenge.is_safety_critical && (
        <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
          <ShieldAlert className="h-3.5 w-3.5" /> Protocolo Crítico de Seguridad
        </span>
      )}
    </div>
  );
}

function VisualConceptCardView({ challenge, disabled, onSubmit }: Props) {
  const payload = challenge.payload_json as {
    card_title: string;
    visual_media_id?: string | null;
    visual_caption?: string;
    key_points: string[];
    check_question: { question: string; options: { id: string; text: string }[] };
  };
  const [selected, setSelected] = useState('');
  const mediaUrl = useSignedMediaUrl(payload.visual_media_id);

  return (
    <div>
      <ChallengeHeader challenge={challenge} />
      <div className="mb-4 rounded-xl bg-[var(--bg-accent-soft)] p-4">
        <h3 className="text-base font-bold text-[var(--brand-primary)]">{payload.card_title}</h3>
        {mediaUrl && (
          <img
            src={mediaUrl}
            alt={payload.card_title}
            className="my-3 max-h-60 w-full rounded-lg border border-[var(--border-subtle)] bg-white object-contain"
          />
        )}
        {payload.visual_caption && <p className="mt-1 text-sm text-[var(--text-secondary)]">{payload.visual_caption}</p>}
        <ul className="mt-3 space-y-1.5 text-sm">
          {payload.key_points.map((pt, i) => (
            <li key={i} className="flex items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand-primary)]" />
              <span>{pt}</span>
            </li>
          ))}
        </ul>
      </div>
      <p className="mb-3 font-semibold">{payload.check_question.question}</p>
      <div className="space-y-2">
        {payload.check_question.options.map((opt) => (
          <button
            key={opt.id}
            type="button"
            disabled={disabled}
            onClick={() => setSelected(opt.id)}
            className={`interactive-card w-full rounded-xl border p-3.5 text-left text-sm font-medium transition ${
              selected === opt.id
                ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)] ring-2 ring-[var(--brand-primary)]/30'
                : 'border-[var(--border-subtle)] bg-white hover:bg-slate-50'
            }`}
          >
            {opt.text}
          </button>
        ))}
      </div>
      <button
        type="button"
        disabled={disabled || !selected}
        onClick={() => onSubmit({ selected_option_id: selected })}
        className="btn-primary mt-5 w-full px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
      >
        Verificar respuesta
      </button>
    </div>
  );
}

function MatchingView({ challenge, disabled, onSubmit }: Props) {
  const payload = challenge.payload_json as {
    instruction: string;
    left_items: { id: string; text: string }[];
    right_items: { id: string; text: string }[];
  };
  const [pairs, setPairs] = useState<Record<string, string>>({});
  const [activeLeftId, setActiveLeftId] = useState<string | null>(payload.left_items[0]?.id ?? null);

  const allPaired = payload.left_items.every((item) => Boolean(pairs[item.id]));

  const findLeftForRight = (rightId: string) =>
    Object.entries(pairs).find(([, rId]) => rId === rightId)?.[0] ?? null;

  const pairCountIndex = (leftId: string) => {
    const idx = payload.left_items.findIndex((item) => item.id === leftId);
    return idx >= 0 ? idx + 1 : 0;
  };

  const handleRightClick = (rightId: string) => {
    if (disabled) return;
    const existingLeft = findLeftForRight(rightId);
    if (existingLeft && !activeLeftId) {
      setPairs((prev) => {
        const copy = { ...prev };
        delete copy[existingLeft];
        return copy;
      });
      return;
    }
    const targetLeft =
      activeLeftId || payload.left_items.find((l) => !pairs[l.id])?.id || null;
    if (!targetLeft) return;

    setPairs((prev) => {
      const updated = { ...prev };
      // Liberar si ese rightId estaba usado en otro par
      for (const [k, v] of Object.entries(updated)) {
        if (v === rightId) delete updated[k];
      }
      updated[targetLeft] = rightId;
      const nextUnpaired = payload.left_items.find((l) => l.id !== targetLeft && !updated[l.id]);
      setActiveLeftId(nextUnpaired?.id ?? null);
      return updated;
    });
  };

  return (
    <div>
      <ChallengeHeader challenge={challenge} />
      <p className="mb-1 text-base font-semibold">{challenge.prompt}</p>
      <p className="mb-4 text-xs text-[var(--text-secondary)]">
        {payload.instruction} — <strong>Toca un elemento de la izquierda y luego su pareja a la derecha.</strong>
      </p>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-2">
          {payload.left_items.map((left, idx) => {
            const isSelected = activeLeftId === left.id;
            const pairedRightId = pairs[left.id];
            return (
              <button
                key={left.id}
                type="button"
                disabled={disabled}
                onClick={() => {
                  if (pairedRightId) {
                    setPairs((prev) => {
                      const next = { ...prev };
                      delete next[left.id];
                      return next;
                    });
                  }
                  setActiveLeftId(left.id);
                }}
                className={`interactive-card flex w-full items-center justify-between gap-2 rounded-xl border p-3 text-left text-sm font-semibold ${
                  isSelected
                    ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)] ring-2 ring-[var(--brand-primary)]/30'
                    : pairedRightId
                      ? 'border-emerald-300 bg-emerald-50/70 text-emerald-950'
                      : 'border-[var(--border-subtle)] bg-white'
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--brand-primary)] text-[11px] font-extrabold text-white">
                    {idx + 1}
                  </span>
                  {left.text}
                </span>
                {pairedRightId && (
                  <span className="rounded-full bg-emerald-600 px-2 py-0.5 text-[10px] font-bold text-white">
                    Conectado
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <div className="space-y-2">
          {payload.right_items.map((right) => {
            const ownerLeftId = findLeftForRight(right.id);
            const ownerNum = ownerLeftId ? pairCountIndex(ownerLeftId) : 0;
            return (
              <button
                key={right.id}
                type="button"
                disabled={disabled}
                onClick={() => handleRightClick(right.id)}
                className={`interactive-card flex w-full items-center justify-between gap-2 rounded-xl border p-3 text-left text-sm font-medium ${
                  ownerLeftId
                    ? 'border-emerald-300 bg-emerald-50/70 text-emerald-950'
                    : activeLeftId
                      ? 'border-dashed border-[var(--brand-primary)]/60 bg-white hover:bg-[var(--bg-accent-soft)]/50'
                      : 'border-[var(--border-subtle)] bg-white'
                }`}
              >
                <span>{right.text}</span>
                {ownerNum > 0 && (
                  <span className="vzt-pop flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-[11px] font-extrabold text-white">
                    {ownerNum}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <button
        type="button"
        disabled={disabled || !allPaired}
        onClick={() => onSubmit({ pairs })}
        className="btn-primary mt-5 w-full px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
      >
        Comprobar emparejamiento ({Object.keys(pairs).length}/{payload.left_items.length})
      </button>
    </div>
  );
}

function SequenceOrderingView({ challenge, disabled, onSubmit }: Props) {
  const payload = challenge.payload_json as {
    instruction: string;
    items: { id: string; text: string }[];
  };
  const [items, setItems] = useState(payload.items);

  const move = (index: number, delta: number) => {
    const next = [...items];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setItems(next);
  };

  return (
    <div>
      <ChallengeHeader challenge={challenge} />
      <p className="mb-1 text-base font-semibold">{challenge.prompt}</p>
      <p className="mb-4 text-xs text-[var(--text-secondary)]">{payload.instruction}</p>
      <ol className="space-y-2.5">
        {items.map((item, idx) => (
          <li
            key={item.id}
            className="interactive-card flex items-center justify-between gap-2 rounded-xl border border-[var(--border-subtle)] bg-white p-3"
          >
            <span className="flex items-center gap-2.5 text-sm font-semibold">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--bg-accent-soft)] text-xs font-extrabold text-[var(--brand-primary)]">
                {idx + 1}
              </span>
              {item.text}
            </span>
            <div className="flex gap-1">
              <button
                type="button"
                disabled={disabled || idx === 0}
                onClick={() => move(idx, -1)}
                aria-label="Subir paso"
                className="rounded-lg border border-[var(--border-subtle)] p-2 hover:bg-slate-100 disabled:opacity-40"
              >
                <ArrowUp className="h-4 w-4" />
              </button>
              <button
                type="button"
                disabled={disabled || idx === items.length - 1}
                onClick={() => move(idx, 1)}
                aria-label="Bajar paso"
                className="rounded-lg border border-[var(--border-subtle)] p-2 hover:bg-slate-100 disabled:opacity-40"
              >
                <ArrowDown className="h-4 w-4" />
              </button>
            </div>
          </li>
        ))}
      </ol>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onSubmit({ ordered_ids: items.map((i) => i.id) })}
        className="btn-primary mt-5 w-full px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
      >
        Enviar secuencia
      </button>
    </div>
  );
}

function InteractiveZonesView({ challenge, disabled, onSubmit }: Props) {
  const payload = challenge.payload_json as {
    instruction: string;
    diagram_media_id?: string | null;
    zones: { id: string; shape: 'circle' | 'rect'; x: number; y: number; r?: number; w?: number; h?: number; label: string }[];
  };
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const diagramUrl = useSignedMediaUrl(payload.diagram_media_id);

  return (
    <div>
      <ChallengeHeader challenge={challenge} />
      <p className="mb-1 text-base font-semibold">{challenge.prompt}</p>
      <p className="mb-4 text-xs text-[var(--text-secondary)]">{payload.instruction}</p>

      <div className="relative overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-slate-900/5">
        {diagramUrl && (
          <img
            src={diagramUrl}
            alt="Diagrama dinámico del reto"
            className="block w-full aspect-[16/9] object-contain bg-white"
          />
        )}
        <svg
          viewBox="0 0 100 56"
          className={diagramUrl ? 'absolute inset-0 h-full w-full' : 'block h-auto w-full'}
          role="img"
          aria-label="Esquema interactivo"
        >
          {!diagramUrl && (
            <>
              {/* Silueta esquemática limpia de referencia */}
              <circle cx="50" cy="14" r="10" fill="#e2e8f0" stroke="#64748b" strokeWidth="0.8" />
              <rect x="43" y="22" width="14" height="16" rx="4" fill="#e2e8f0" stroke="#64748b" strokeWidth="0.8" />
              <path d="M22 44 Q50 34 78 44 L82 55 L18 55 Z" fill="#cbd5e1" stroke="#64748b" strokeWidth="0.8" />
            </>
          )}

          {payload.zones.map((z) => {
            const active = selectedZoneId === z.id;
            const cx = z.x * 100;
            const cy = z.y * 56;
            if (z.shape === 'circle') {
              return (
                <circle
                  key={z.id}
                  cx={cx}
                  cy={cy}
                  r={(z.r ?? 0.08) * 56}
                  fill={active ? 'rgba(15, 76, 92, 0.45)' : 'rgba(217, 119, 6, 0.22)'}
                  stroke={active ? '#0f4c5c' : '#d97706'}
                  strokeWidth="1.2"
                  className="cursor-pointer"
                  onClick={() => !disabled && setSelectedZoneId(z.id)}
                />
              );
            }
            return (
              <rect
                key={z.id}
                x={cx}
                y={cy}
                width={(z.w ?? 0.2) * 100}
                height={(z.h ?? 0.1) * 56}
                rx="1.5"
                fill={active ? 'rgba(15, 76, 92, 0.45)' : 'rgba(217, 119, 6, 0.22)'}
                stroke={active ? '#0f4c5c' : '#d97706'}
                strokeWidth="1.2"
                className="cursor-pointer"
                onClick={() => !disabled && setSelectedZoneId(z.id)}
              />
            );
          })}
        </svg>
      </div>

      {/* Controles accesibles por teclado/pantalla táctil */}
      <div className="mt-3 flex flex-wrap gap-2">
        {payload.zones.map((z) => (
          <button
            key={z.id}
            type="button"
            disabled={disabled}
            onClick={() => setSelectedZoneId(z.id)}
            className={`rounded-lg border px-3 py-1.5 text-xs font-semibold ${
              selectedZoneId === z.id
                ? 'border-[var(--brand-primary)] bg-[var(--brand-primary)] text-white'
                : 'border-[var(--border-subtle)] bg-white text-[var(--text-primary)]'
            }`}
          >
            {z.label}
          </button>
        ))}
      </div>

      <button
        type="button"
        disabled={disabled || !selectedZoneId}
        onClick={() => onSubmit({ selected_zone_ids: selectedZoneId ? [selectedZoneId] : [] })}
        className="btn-primary mt-5 w-full px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
      >
        Confirmar zona
      </button>
    </div>
  );
}

function DecisionSimulationView({ challenge, disabled, onSubmit }: Props) {
  const payload = challenge.payload_json as {
    scenario_context: string;
    initial_node_id: string;
    nodes: Record<
      string,
      {
        narrative?: string;
        choices?: { id: string; text: string; next_node_id: string }[];
        is_terminal?: boolean;
        summary?: string;
      }
    >;
  };

  const [currentNodeId, setCurrentNodeId] = useState(payload.initial_node_id);
  const [chosenSequence, setChosenSequence] = useState<string[]>([]);
  const node = payload.nodes[currentNodeId];

  const handleChoice = (choiceId: string, nextNodeId: string) => {
    const updated = [...chosenSequence, choiceId];
    setChosenSequence(updated);
    setCurrentNodeId(nextNodeId);
    if (payload.nodes[nextNodeId]?.is_terminal) {
      onSubmit({ chosen_sequence: updated });
    }
  };

  return (
    <div>
      <ChallengeHeader challenge={challenge} />
      <p className="mb-2 text-base font-semibold">{challenge.prompt}</p>
      <div className="mb-4 rounded-xl bg-slate-100 p-3.5 text-sm text-[var(--text-secondary)]">
        {payload.scenario_context}
      </div>

      {node?.is_terminal ? (
        <div className="rounded-xl border border-[var(--border-subtle)] p-4">
          <p className="font-semibold text-sm">{node.summary}</p>
          <button
            type="button"
            disabled={disabled}
            onClick={() => {
              setCurrentNodeId(payload.initial_node_id);
              setChosenSequence([]);
            }}
            className="mt-3 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs font-semibold"
          >
            Reiniciar simulación
          </button>
        </div>
      ) : (
        <div>
          <p key={currentNodeId} className="vzt-scale-in mb-3 font-semibold text-sm">{node?.narrative}</p>
          <div className="space-y-2">
            {(node?.choices ?? []).map((ch) => (
              <button
                key={ch.id}
                type="button"
                disabled={disabled}
                onClick={() => handleChoice(ch.id, ch.next_node_id)}
                className="interactive-card w-full rounded-xl border border-[var(--border-subtle)] bg-white p-3.5 text-left text-sm font-medium hover:border-[var(--brand-primary)] hover:bg-[var(--bg-accent-soft)]"
              >
                {ch.text}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function FillInBlanksView({ challenge, disabled, onSubmit }: Props) {
  const payload = challenge.payload_json as {
    template: string;
    word_bank: string[];
    blanks: { id: string; label: string }[];
  };
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [activeBlankId, setActiveBlankId] = useState<string | null>(payload.blanks[0]?.id ?? null);
  const allFilled = payload.blanks.every((b) => Boolean(answers[b.id]?.trim()));
  const usedWords = new Set(Object.values(answers).filter(Boolean));

  const handlePickWord = (word: string) => {
    if (disabled) return;
    const targetId =
      activeBlankId || payload.blanks.find((b) => !answers[b.id])?.id || payload.blanks[0]?.id;
    if (!targetId) return;
    setAnswers((prev) => {
      const next = { ...prev, [targetId]: word };
      const nextEmpty = payload.blanks.find((b) => b.id !== targetId && !next[b.id]);
      setActiveBlankId(nextEmpty?.id ?? null);
      return next;
    });
  };

  return (
    <div>
      <ChallengeHeader challenge={challenge} />
      <p className="mb-3 text-base font-semibold">{challenge.prompt}</p>
      <div className="mb-4 rounded-xl bg-[var(--bg-accent-soft)] p-4 text-sm leading-relaxed">
        {payload.template}
      </div>

      {payload.word_bank.length > 0 ? (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            {payload.blanks.map((blank) => {
              const val = answers[blank.id] ?? '';
              const isFocused = activeBlankId === blank.id;
              return (
                <button
                  key={blank.id}
                  type="button"
                  disabled={disabled}
                  onClick={() => {
                    if (val) {
                      setAnswers((prev) => {
                        const copy = { ...prev };
                        delete copy[blank.id];
                        return copy;
                      });
                    }
                    setActiveBlankId(blank.id);
                  }}
                  className={`interactive-card flex flex-col items-start rounded-xl border p-3 text-left transition ${
                    isFocused
                      ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)] ring-2 ring-[var(--brand-primary)]/25'
                      : val
                        ? 'border-emerald-300 bg-emerald-50/70'
                        : 'border-dashed border-[var(--border-subtle)] bg-white'
                  }`}
                >
                  <span className="text-[11px] font-bold uppercase text-[var(--text-secondary)]">
                    {blank.label}
                  </span>
                  <span className={`mt-1 text-sm font-bold ${val ? 'text-emerald-900' : 'text-slate-400'}`}>
                    {val || 'Toca palabra abajo...'}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="space-y-2">
            <p className="text-xs font-semibold text-[var(--text-secondary)]">
              Toca las fichas para completar los espacios (toca un espacio lleno para quitar):
            </p>
            <div className="flex flex-wrap gap-2">
              {payload.word_bank.map((word) => {
                const isUsed = usedWords.has(word);
                return (
                  <button
                    key={word}
                    type="button"
                    disabled={disabled || isUsed}
                    onClick={() => handlePickWord(word)}
                    className={`rounded-full border px-3.5 py-1.5 text-xs font-bold transition ${
                      isUsed
                        ? 'border-slate-200 bg-slate-100 text-slate-400 line-through'
                        : 'interactive-card border-[var(--brand-primary)]/40 bg-white text-[var(--brand-primary)] hover:bg-[var(--bg-accent-soft)]'
                    }`}
                  >
                    {word}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-3">
          {payload.blanks.map((blank) => (
            <label key={blank.id} className="block text-xs font-semibold text-[var(--text-secondary)]">
              {blank.label} ({`{{${blank.id}}}`})
              <input
                disabled={disabled}
                type="text"
                value={answers[blank.id] ?? ''}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [blank.id]: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm text-[var(--text-primary)]"
              />
            </label>
          ))}
        </div>
      )}

      <button
        type="button"
        disabled={disabled || !allFilled}
        onClick={() => onSubmit({ answers })}
        className="btn-primary mt-5 w-full px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
      >
        Comprobar respuestas
      </button>
    </div>
  );
}

function OpenResponseView({ challenge, disabled, onSubmit }: Props) {
  const payload = challenge.payload_json as {
    instruction?: string;
    min_words?: number;
    keywords_expected?: string[];
  };
  const [responseText, setResponseText] = useState('');
  const minWords = payload.min_words ?? 8;
  const wordCount = responseText.trim() ? responseText.trim().split(/\s+/).length : 0;

  return (
    <div>
      <ChallengeHeader challenge={challenge} />
      <p className="mb-2 text-base font-semibold">{challenge.prompt}</p>
      {payload.instruction && (
        <div className="mb-3 rounded-xl bg-[var(--bg-accent-soft)] p-3.5 text-sm text-[var(--text-secondary)]">
          {payload.instruction}
        </div>
      )}
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs text-[var(--text-secondary)]">
          Palabras escritas: <strong>{wordCount}</strong> (mínimo sugerido: {minWords})
        </span>
        <DictationButton
          disabled={disabled}
          onTranscript={(spoken) =>
            setResponseText((prev) => (prev.trim() ? `${prev.trim()} ${spoken}` : spoken))
          }
        />
      </div>
      <textarea
        rows={5}
        disabled={disabled}
        value={responseText}
        onChange={(e) => setResponseText(e.target.value)}
        placeholder="Desarrolla tu respuesta abierta o utiliza el dictado por voz..."
        className="w-full rounded-xl border border-[var(--border-subtle)] bg-white p-3.5 text-sm"
      />
      <button
        type="button"
        disabled={disabled || wordCount < 1}
        onClick={() => onSubmit({ response_text: responseText.trim() })}
        className="btn-primary mt-4 w-full px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
      >
        Enviar respuesta para evaluación IA y docente
      </button>
    </div>
  );
}
