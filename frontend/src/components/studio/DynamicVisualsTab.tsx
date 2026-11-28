import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ImagePlus, Sparkles, Trash2, Upload } from 'lucide-react';
import { EmptyState, ErrorBanner, LoadingState, SuccessBanner } from '../ui/StatusStates';
import { apiRequest, resolveAssetUrl } from '../../services/apiClient';
import type { DiagramKind, GenerateDynamicVisualResponse, MediaAssetOut } from '../../types/api';
import { scopePrefix, type StudioScope } from './studioHelpers';

interface Props {
  scope: StudioScope;
  selectedLessonVersionId?: string;
}

export function DynamicVisualsTab({ scope, selectedLessonVersionId }: Props) {
  const queryClient = useQueryClient();
  const prefix = scopePrefix(scope);
  const [feedback, setFeedback] = useState<string | null>(null);

  // IA Dynamic Visual
  const [aiTopic, setAiTopic] = useState('');
  const [diagramKind, setDiagramKind] = useState<DiagramKind>('auto');
  const [aiContext, setAiContext] = useState('');
  const [attachAsChallenge, setAttachAsChallenge] = useState(false);

  // Constructor Manual Dinámico
  const [manTitle, setManTitle] = useState('');
  const [manTemplate, setManTemplate] = useState<'flowchart' | 'cycle' | 'hierarchy' | 'comparison' | 'layers'>('flowchart');
  const [manNodesText, setManNodesText] = useState('Fase 1 | Evaluar entorno\nFase 2 | Aplicar protocolo\nFase 3 | Validar resultado');

  // Subida archivo
  const [upTitle, setUpTitle] = useState('');
  const [upTags, setUpTags] = useState('');
  const [upFile, setUpFile] = useState<File | null>(null);

  const mediaQuery = useQuery({
    queryKey: ['studio-media', prefix],
    queryFn: () => apiRequest<MediaAssetOut[]>(`${prefix}/media`),
  });

  const generateVisualMutation = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      return apiRequest<GenerateDynamicVisualResponse>(`${prefix}/ai/generate-dynamic-visual`, {
        method: 'POST',
        body: JSON.stringify({
          topic: aiTopic,
          diagram_kind: diagramKind,
          context_text: aiContext,
          lesson_version_id: attachAsChallenge && selectedLessonVersionId ? selectedLessonVersionId : null,
          create_interactive_challenge: attachAsChallenge && Boolean(selectedLessonVersionId),
        }),
      });
    },
    onSuccess: (res) => {
      setAiTopic('');
      setAiContext('');
      setFeedback(
        res.created_challenge_id
          ? `Imagen dinámica "${res.title}" creada y enlazada como reto interactivo (${res.template}).`
          : `Imagen dinámica "${res.title}" creada (${res.template}) vía ${res.provider}.`
      );
      void queryClient.invalidateQueries({ queryKey: ['studio-media', prefix] });
      if (res.created_challenge_id) {
        void queryClient.invalidateQueries({ queryKey: ['studio-challenges', prefix, selectedLessonVersionId] });
      }
    },
  });

  const createManualDynamic = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      const nodes = manNodesText
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .slice(0, 6)
        .map((line, idx) => {
          const [label, detail] = line.split('|').map((s) => s.trim());
          return {
            id: `z${idx + 1}`,
            label: label || `Nodo ${idx + 1}`,
            detail: detail || '',
            badge: `${idx + 1}`,
          };
        });
      return apiRequest<MediaAssetOut>(`${prefix}/media/dynamic`, {
        method: 'POST',
        body: JSON.stringify({
          title: manTitle,
          description: `Diagrama dinámico manual (${manTemplate})`,
          tags: [manTemplate, 'manual'],
          visibility: scope.mode === 'global' ? 'public' : 'institutional',
          dynamic_spec: { title: manTitle, template: manTemplate, nodes },
        }),
      });
    },
    onSuccess: (res) => {
      setManTitle('');
      setFeedback(`Diagrama dinámico "${res.title}" guardado en tu galería.`);
      void queryClient.invalidateQueries({ queryKey: ['studio-media', prefix] });
    },
  });

  const uploadFileMutation = useMutation({
    mutationFn: (e: React.FormEvent) => {
      e.preventDefault();
      if (!upFile) throw new Error('Selecciona un archivo primero');
      const form = new FormData();
      form.append('title', upTitle || upFile.name);
      form.append('tags', upTags);
      form.append('visibility', scope.mode === 'global' ? 'public' : 'institutional');
      form.append('file', upFile);
      return apiRequest<MediaAssetOut>(`${prefix}/media`, { method: 'POST', body: form });
    },
    onSuccess: (res) => {
      setUpTitle('');
      setUpTags('');
      setUpFile(null);
      setFeedback(`Archivo "${res.title}" subido correctamente.`);
      void queryClient.invalidateQueries({ queryKey: ['studio-media', prefix] });
    },
  });

  const deleteMediaMutation = useMutation({
    mutationFn: (id: string) => apiRequest<void>(`${prefix}/media/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      setFeedback('Recurso multimedia eliminado.');
      void queryClient.invalidateQueries({ queryKey: ['studio-media', prefix] });
    },
  });

  const generateIllustrationMutation = useMutation({
    mutationFn: () =>
      apiRequest<MediaAssetOut>(`${prefix}/media/ai-illustration`, {
        method: 'POST',
        body: JSON.stringify({
          topic: aiTopic || 'Diagrama educativo',
          style: 'scientific',
          visibility: scope.mode === 'global' ? 'public' : 'institutional',
        }),
      }),
    onSuccess: (res) => {
      setFeedback(`Ilustración generada (${res.mime_type}): "${res.title}".`);
      void queryClient.invalidateQueries({ queryKey: ['studio-media', prefix] });
    },
  });

  const err =
    generateVisualMutation.error ||
    generateIllustrationMutation.error ||
    createManualDynamic.error ||
    uploadFileMutation.error ||
    deleteMediaMutation.error;

  return (
    <div className="space-y-5">
      {feedback && <SuccessBanner message={feedback} />}
      {err && <ErrorBanner message={(err as Error).message} />}

      <div className="grid gap-5 lg:grid-cols-2">
        {/* Generador IA */}
        <form onSubmit={generateVisualMutation.mutate} className="surface-card p-5 space-y-3">
          <h2 className="flex items-center gap-2 text-base font-bold">
            <Sparkles className="h-5 w-5 text-[var(--brand-primary)]" /> Generador IA de Imágenes Dinámicas SVG
          </h2>
          <p className="text-xs text-[var(--text-secondary)]">
            Describe cualquier concepto, proceso o jerarquía. Se genera un diagrama vectorial interactivo persistente en base de datos.
          </p>
          <input
            required
            minLength={3}
            placeholder="Tema del diagrama (ej. Ciclo de Krebs, Triaje START, Ley de Ohm)"
            value={aiTopic}
            onChange={(e) => setAiTopic(e.target.value)}
            className="w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
          />
          <select
            value={diagramKind}
            onChange={(e) => setDiagramKind(e.target.value as DiagramKind)}
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
          >
            <option value="auto">Plantilla automática inteligente</option>
            <option value="flowchart">Flujo paso a paso</option>
            <option value="cycle">Ciclo continuo</option>
            <option value="hierarchy">Mapa conceptual / jerarquía</option>
            <option value="comparison">Cuadro comparativo</option>
            <option value="layers">Capas / Pirámide de prioridades</option>
          </select>
          <textarea
            rows={3}
            placeholder="Notas o conceptos que debe incluir el diagrama (opcional)..."
            value={aiContext}
            onChange={(e) => setAiContext(e.target.value)}
            className="w-full rounded-lg border border-[var(--border-subtle)] p-2.5 text-sm"
          />
          {selectedLessonVersionId && (
            <label className="flex items-center gap-2 text-xs font-medium">
              <input
                type="checkbox"
                checked={attachAsChallenge}
                onChange={(e) => setAttachAsChallenge(e.target.checked)}
              />
              Crear automáticamente un reto de <strong>Zonas Interactivas</strong> en la versión seleccionada
            </label>
          )}
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={generateVisualMutation.isPending} className="btn-primary flex-1 py-2 text-xs font-bold">
              {generateVisualMutation.isPending ? 'Generando imagen dinámica...' : 'Generar Diagrama Interactivo IA'}
            </button>
            <button
              type="button"
              disabled={!aiTopic.trim() || generateIllustrationMutation.isPending}
              onClick={() => generateIllustrationMutation.mutate()}
              className="rounded-xl border border-[var(--brand-primary)] bg-white px-3 py-2 text-xs font-bold text-[var(--brand-primary)] hover:bg-[var(--bg-accent-soft)] disabled:opacity-50"
            >
              {generateIllustrationMutation.isPending ? 'Ilustrando...' : 'Ilustración IA Real'}
            </button>
          </div>
        </form>

        {/* Constructor manual + subida */}
        <div className="space-y-5">
          <form onSubmit={createManualDynamic.mutate} className="surface-card p-5 space-y-3">
            <h2 className="flex items-center gap-2 text-base font-bold">
              <ImagePlus className="h-5 w-5 text-[var(--brand-primary)]" /> Constructor Manual de Diagrama Dinámico
            </h2>
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                required
                placeholder="Título del esquema"
                value={manTitle}
                onChange={(e) => setManTitle(e.target.value)}
                className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
              />
              <select
                value={manTemplate}
                onChange={(e) => setManTemplate(e.target.value as typeof manTemplate)}
                className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
              >
                <option value="flowchart">Flujo</option>
                <option value="cycle">Ciclo</option>
                <option value="hierarchy">Jerarquía</option>
                <option value="comparison">Comparativa</option>
                <option value="layers">Capas</option>
              </select>
            </div>
            <textarea
              rows={3}
              value={manNodesText}
              onChange={(e) => setManNodesText(e.target.value)}
              placeholder="Un nodo por línea: Título | Detalle"
              className="w-full rounded-lg border border-[var(--border-subtle)] p-2.5 text-xs font-mono"
            />
            <button type="submit" disabled={createManualDynamic.isPending} className="btn-primary w-full py-2 text-xs font-semibold">
              Construir y Guardar Diagrama
            </button>
          </form>

          <form onSubmit={uploadFileMutation.mutate} className="surface-card p-5 space-y-2.5">
            <h3 className="flex items-center gap-2 text-sm font-bold">
              <Upload className="h-4 w-4 text-[var(--brand-primary)]" /> Subir Imagen, GIF, SVG, Audio o PDF Propio
            </h3>
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                placeholder="Título del recurso"
                value={upTitle}
                onChange={(e) => setUpTitle(e.target.value)}
                className="rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs"
              />
              <input
                placeholder="Etiquetas (coma separada)"
                value={upTags}
                onChange={(e) => setUpTags(e.target.value)}
                className="rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs"
              />
            </div>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml,application/pdf,audio/mpeg,audio/webm,audio/ogg,audio/wav"
              onChange={(e) => setUpFile(e.target.files?.[0] ?? null)}
              className="w-full text-xs"
            />
            <button type="submit" disabled={uploadFileMutation.isPending || !upFile} className="btn-primary w-full py-1.5 text-xs font-semibold disabled:opacity-50">
              Subir Archivo
            </button>
          </form>
        </div>
      </div>

      {/* Galería CRUD */}
      <section className="surface-card p-5 space-y-3">
        <h3 className="text-sm font-bold uppercase text-[var(--text-secondary)]">
          Galería Visual del Ámbito ({mediaQuery.data?.length ?? 0})
        </h3>
        {mediaQuery.isLoading ? (
          <LoadingState label="Cargando galería visual..." />
        ) : !mediaQuery.data?.length ? (
          <EmptyState title="Galería vacía" description="Genera una imagen dinámica arriba o sube un recurso propio." />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {mediaQuery.data.map((m) => (
              <div key={m.id} className="rounded-xl border border-[var(--border-subtle)] bg-white p-3 space-y-2">
                {m.signed_url && m.media_format === 'audio_clip' ? (
                  <audio controls src={resolveAssetUrl(m.signed_url)} className="w-full py-4" />
                ) : (
                  m.signed_url &&
                  m.media_format !== 'pdf' && (
                    <img
                      src={resolveAssetUrl(m.signed_url)}
                      alt={m.title}
                      className="h-40 w-full rounded-lg bg-slate-50 object-contain"
                    />
                  )
                )}
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-bold text-xs">{m.title}</p>
                    <p className="text-[11px] text-[var(--text-secondary)]">
                      {m.media_format} • {m.visibility}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => deleteMediaMutation.mutate(m.id)}
                    className="rounded border border-red-200 p-1 text-red-700 hover:bg-red-50"
                    aria-label="Eliminar recurso visual"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
                <p className="text-[10px] font-mono text-slate-500 truncate">ID: {m.id}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
