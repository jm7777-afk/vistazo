import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowDown, ArrowUp, CheckCircle2, ShieldAlert } from 'lucide-react';
import { apiRequest, resolveAssetUrl } from '../../services/apiClient';
import type { ChallengePublic } from '../../types/api';

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
    default:
      return <p className="text-sm text-red-600">Tipo de reto no soportado.</p>;
  }
}

function ChallengeHeader({ challenge }: { challenge: ChallengePublic }) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
      <span className="rounded-full bg-[var(--bg-accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--brand-primary)]">
        {challenge.challenge_type.replace(/_/g, ' ')} • {challenge.points} pts
      </span>
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
            className={`w-full rounded-xl border p-3.5 text-left text-sm font-medium transition ${
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

  const allPaired = payload.left_items.every((item) => Boolean(pairs[item.id]));

  return (
    <div>
      <ChallengeHeader challenge={challenge} />
      <p className="mb-4 text-base font-semibold">{challenge.prompt}</p>
      <p className="mb-3 text-xs text-[var(--text-secondary)]">{payload.instruction}</p>
      <div className="space-y-3">
        {payload.left_items.map((left) => (
          <div key={left.id} className="flex flex-col gap-2 rounded-xl border border-[var(--border-subtle)] p-3 sm:flex-row sm:items-center sm:justify-between">
            <span className="font-semibold text-sm">{left.text}</span>
            <select
              disabled={disabled}
              value={pairs[left.id] ?? ''}
              onChange={(e) => setPairs((prev) => ({ ...prev, [left.id]: e.target.value }))}
              className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
            >
              <option value="">Selecciona correspondencia...</option>
              {payload.right_items.map((right) => (
                <option key={right.id} value={right.id}>
                  {right.text}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
      <button
        type="button"
        disabled={disabled || !allPaired}
        onClick={() => onSubmit({ pairs })}
        className="btn-primary mt-5 w-full px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
      >
        Comprobar emparejamiento
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
      <ol className="space-y-2">
        {items.map((item, idx) => (
          <li key={item.id} className="flex items-center justify-between gap-2 rounded-xl border border-[var(--border-subtle)] bg-white p-3">
            <span className="text-sm font-medium">
              <strong className="mr-2 text-[var(--brand-primary)]">{idx + 1}.</strong>
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
          <p className="mb-3 font-semibold text-sm">{node?.narrative}</p>
          <div className="space-y-2">
            {(node?.choices ?? []).map((ch) => (
              <button
                key={ch.id}
                type="button"
                disabled={disabled}
                onClick={() => handleChoice(ch.id, ch.next_node_id)}
                className="w-full rounded-xl border border-[var(--border-subtle)] bg-white p-3.5 text-left text-sm font-medium hover:border-[var(--brand-primary)] hover:bg-[var(--bg-accent-soft)]"
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
  const allFilled = payload.blanks.every((b) => Boolean(answers[b.id]?.trim()));

  return (
    <div>
      <ChallengeHeader challenge={challenge} />
      <p className="mb-3 text-base font-semibold">{challenge.prompt}</p>
      <div className="mb-4 rounded-xl bg-[var(--bg-accent-soft)] p-4 text-sm leading-relaxed">
        {payload.template}
      </div>
      {payload.word_bank.length > 0 && (
        <p className="mb-3 text-xs text-[var(--text-secondary)]">
          Banco sugerido: <strong>{payload.word_bank.join(' · ')}</strong>
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-3">
        {payload.blanks.map((blank) => (
          <label key={blank.id} className="block text-xs font-semibold text-[var(--text-secondary)]">
            {blank.label} ({`{{${blank.id}}}`})
            {payload.word_bank.length > 0 ? (
              <select
                disabled={disabled}
                value={answers[blank.id] ?? ''}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [blank.id]: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm text-[var(--text-primary)]"
              >
                <option value="">Elegir...</option>
                {payload.word_bank.map((w) => (
                  <option key={w} value={w}>
                    {w}
                  </option>
                ))}
              </select>
            ) : (
              <input
                disabled={disabled}
                type="text"
                value={answers[blank.id] ?? ''}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [blank.id]: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm text-[var(--text-primary)]"
              />
            )}
          </label>
        ))}
      </div>
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
