import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { FileUp, Layers, Sparkles, Wand2 } from 'lucide-react';
import { ErrorBanner, SuccessBanner } from '../ui/StatusStates';
import { apiRequest } from '../../services/apiClient';
import type { DocumentExtractResponse, GenerateBlueprintResponse, PedagogyStyle, UIProfile } from '../../types/api';
import { readTextDocument, scopePrefix, type StudioScope } from './studioHelpers';

interface Props {
  scope: StudioScope;
  onCourseCreated: (courseId: string) => void;
}

export function BlueprintTab({ scope, onCourseCreated }: Props) {
  const queryClient = useQueryClient();
  const prefix = scopePrefix(scope);

  const [topic, setTopic] = useState('');
  const [educationLevel, setEducationLevel] = useState('specialized');
  const [uiProfile, setUiProfile] = useState<UIProfile>('pro');
  const [pedagogyStyle, setPedagogyStyle] = useState<PedagogyStyle>('active_recall');
  const [modulesCount, setModulesCount] = useState(3);
  const [sourceText, setSourceText] = useState('');
  const [saveImmediately, setSaveImmediately] = useState(true);
  const [preview, setPreview] = useState<GenerateBlueprintResponse | null>(null);
  const [uploadName, setUploadName] = useState<string | null>(null);

  const blueprintMutation = useMutation({
    mutationFn: (persist: boolean) =>
      apiRequest<GenerateBlueprintResponse>(`${prefix}/ai/generate-blueprint`, {
        method: 'POST',
        body: JSON.stringify({
          topic,
          education_level: educationLevel,
          ui_profile: uiProfile,
          pedagogy_style: pedagogyStyle,
          modules_count: modulesCount,
          source_text: sourceText,
          save_to_course: persist,
        }),
      }),
    onSuccess: (res) => {
      setPreview(res);
      if (res.created_course_id) {
        void queryClient.invalidateQueries({ queryKey: ['studio-courses', prefix] });
        void queryClient.invalidateQueries({ queryKey: ['studio-guides', prefix] });
        onCourseCreated(res.created_course_id);
      }
    },
  });

  const [extractError, setExtractError] = useState<string | null>(null);

  const handleFileLoad = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setExtractError(null);
    const lower = file.name.toLowerCase();
    if (lower.endsWith('.pdf') || lower.endsWith('.docx')) {
      try {
        const form = new FormData();
        form.append('file', file);
        const extracted = await apiRequest<DocumentExtractResponse>(`${prefix}/ai/extract-document`, {
          method: 'POST',
          body: form,
        });
        setSourceText(extracted.extracted_text);
        setUploadName(`${extracted.filename} (${extracted.char_count} chars extraídos)`);
      } catch (err) {
        setExtractError((err as Error).message);
      }
      return;
    }
    const text = await readTextDocument(file);
    setSourceText(text);
    setUploadName(file.name);
  };

  return (
    <div className="space-y-5">
      <div className="surface-card p-5 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h2 className="flex items-center gap-2 text-base font-bold">
              <Wand2 className="h-5 w-5 text-[var(--brand-primary)]" />
              Arquitecto IA de Materias, Metodología, Pensum y Nodos
            </h2>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              Sube un temario/guía (.txt, .md, .csv, .json) o describe tu materia. La IA organiza módulos, nodos
              (incluyendo Prueba Fuerte de cierre), metodología y guía de estudio profesional.
            </p>
          </div>
          <span className="rounded-full bg-[var(--bg-accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--brand-primary)]">
            Ámbito: {scope.label}
          </span>
        </div>

        {blueprintMutation.error && <ErrorBanner message={(blueprintMutation.error as Error).message} />}
        {extractError && <ErrorBanner message={extractError} />}
        {preview?.created_course_id && (
          <SuccessBanner
            message={`Curso "${preview.blueprint.course_title}" guardado con ${preview.blueprint.modules.length} módulos y guía metodológica (${preview.provider}). Ya puedes editarlo en Materias y Nodos.`}
          />
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            blueprintMutation.mutate(saveImmediately);
          }}
          className="space-y-3.5"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-xs font-semibold">
              Materia o Tema principal
              <input
                required
                minLength={3}
                placeholder="Ej. Biología Celular, Cálculo I, Triaje START..."
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-xs font-semibold">
              Metodología de aprendizaje y repaso
              <select
                value={pedagogyStyle}
                onChange={(e) => setPedagogyStyle(e.target.value as PedagogyStyle)}
                className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
              >
                <option value="active_recall">Recuperación Activa + Micro-retos</option>
                <option value="problem_based">Aprendizaje Basado en Casos Reales</option>
                <option value="flipped_mastery">Aula Invertida por Dominio</option>
                <option value="spaced_microlearning">Microlearning Espaciado SM-2</option>
              </select>
            </label>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block text-xs font-semibold">
              Nivel educativo
              <select
                value={educationLevel}
                onChange={(e) => setEducationLevel(e.target.value)}
                className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
              >
                <option value="primary">Primaria</option>
                <option value="secondary">Secundaria</option>
                <option value="high_school">Bachillerato</option>
                <option value="university">Universidad</option>
                <option value="technical">Técnico</option>
                <option value="specialized">Especializado</option>
                <option value="rescue">Rescate / Emergencias</option>
              </select>
            </label>
            <label className="block text-xs font-semibold">
              Perfil visual
              <select
                value={uiProfile}
                onChange={(e) => setUiProfile(e.target.value as UIProfile)}
                className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
              >
                <option value="pro">Profesional / Técnico</option>
                <option value="youth">Juvenil / Dinámico</option>
                <option value="kids">Infantil / Visual</option>
              </select>
            </label>
            <label className="block text-xs font-semibold">
              Módulos a estructurar
              <input
                type="number"
                min={2}
                max={5}
                value={modulesCount}
                onChange={(e) => setModulesCount(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
              />
            </label>
          </div>

          <div className="rounded-xl border border-dashed border-[var(--border-subtle)] bg-slate-50 p-3 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="flex items-center gap-1.5 text-xs font-semibold">
                <FileUp className="h-4 w-4 text-[var(--brand-primary)]" />
                Cargar archivo de temario / guía (.pdf, .docx, .txt, .md)
              </span>
              <input
                type="file"
                accept=".pdf,.docx,.txt,.md,.csv,.json"
                onChange={(e) => void handleFileLoad(e)}
                className="text-xs"
              />
            </div>
            {uploadName && <p className="text-[11px] text-emerald-700 font-semibold">Archivo cargado: {uploadName}</p>}
            <textarea
              rows={5}
              placeholder="O pega aquí tu temario, apuntes, objetivos, pensum o material base para que la IA lo organice..."
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-white p-3 text-sm"
            />
          </div>

          <label className="flex items-center gap-2 text-xs font-medium">
            <input
              type="checkbox"
              checked={saveImmediately}
              onChange={(e) => setSaveImmediately(e.target.checked)}
            />
            Crear automáticamente la Materia, Módulos, Nodos y Guía de Estudio en borrador
          </label>

          <button type="submit" disabled={blueprintMutation.isPending} className="btn-primary inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold">
            <Sparkles className="h-4 w-4" />
            {blueprintMutation.isPending
              ? 'Diseñando estructura y metodología...'
              : saveImmediately
                ? 'Generar y guardar estructura completa'
                : 'Solo previsualizar propuesta IA'}
          </button>
        </form>
      </div>

      {preview && (
        <div className="surface-card p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-base font-bold">{preview.blueprint.course_title}</h3>
              <p className="text-xs text-[var(--text-secondary)]">{preview.blueprint.course_description}</p>
            </div>
            <span className="rounded bg-slate-100 px-2.5 py-1 text-xs font-semibold">
              Proveedor: {preview.provider}
            </span>
          </div>

          <div className="rounded-xl bg-[var(--bg-accent-soft)] p-4 text-xs space-y-1.5">
            <p className="font-bold text-[var(--brand-primary)]">Metodología y Forma de Estudio Sugerida</p>
            <p>
              <strong>Enfoque:</strong> {String(preview.blueprint.methodology.pedagogical_approach ?? '')}
            </p>
            <p>
              <strong>Ritmo:</strong> {String(preview.blueprint.methodology.study_rhythm ?? '')}
            </p>
            <p>
              <strong>Estrategia de repaso:</strong> {String(preview.blueprint.methodology.recall_strategy ?? '')}
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            {preview.blueprint.modules.map((m, idx) => (
              <div key={idx} className="rounded-xl border border-[var(--border-subtle)] bg-white p-3.5 space-y-2">
                <p className="flex items-center gap-1.5 text-sm font-bold">
                  <Layers className="h-4 w-4 text-[var(--brand-primary)]" /> {m.title}
                </p>
                <ul className="space-y-1 text-xs">
                  {m.lessons.map((l, j) => (
                    <li key={j} className="rounded bg-slate-50 px-2 py-1.5">
                      <span className="font-semibold">{l.title}</span>
                      <span className="block text-[11px] text-[var(--text-secondary)]">
                        {l.lesson_type} • {l.estimated_minutes} min • Min {l.passing_score_pct}%
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
