import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { BookMarked, ChevronDown, ChevronUp, Clock, Flame, Play, ShieldAlert } from 'lucide-react';
import { EmptyState, ErrorBanner, LoadingState } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import type { CourseDetail, StudyGuideOut } from '../types/api';

export function CourseDetailPage() {
  const { courseId } = useParams<{ courseId: string }>();
  const [searchParams] = useSearchParams();
  const classroomId = searchParams.get('classroomId');
  const [openGuideId, setOpenGuideId] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['course-detail', courseId],
    queryFn: () => apiRequest<CourseDetail>(`/courses/${courseId}`),
    enabled: Boolean(courseId),
  });

  const guidesQuery = useQuery({
    queryKey: ['course-study-guides', courseId],
    queryFn: () => apiRequest<StudyGuideOut[]>(`/courses/${courseId}/study-guides`),
    enabled: Boolean(courseId),
  });

  if (isLoading) return <LoadingState label="Cargando mapa de aprendizaje..." />;
  if (error) return <ErrorBanner message={(error as Error).message} onRetry={() => void refetch()} />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="surface-card p-6">
        <span className="rounded-full bg-[var(--bg-accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--brand-primary)]">
          {data.visibility === 'public' ? 'Estudio Libre' : 'Curso Institucional'} • {data.education_level}
        </span>
        <h1 className="mt-3 text-2xl font-bold">{data.title}</h1>
        {data.description && <p className="mt-1.5 text-sm text-[var(--text-secondary)]">{data.description}</p>}
      </div>

      {guidesQuery.data && guidesQuery.data.length > 0 && (
        <section className="surface-card p-5 space-y-3">
          <h2 className="flex items-center gap-2 text-base font-bold">
            <BookMarked className="h-5 w-5 text-[var(--brand-primary)]" /> Guías de Estudio, Temario y Metodología
          </h2>
          <div className="space-y-2">
            {guidesQuery.data.map((g) => {
              const isOpen = openGuideId === g.id;
              return (
                <div key={g.id} className="rounded-xl border border-[var(--border-subtle)] bg-white">
                  <button
                    type="button"
                    onClick={() => setOpenGuideId(isOpen ? null : g.id)}
                    className="flex w-full items-center justify-between px-4 py-3 text-left"
                  >
                    <div>
                      <span className="rounded bg-[var(--bg-accent-soft)] px-2 py-0.5 text-[11px] font-bold text-[var(--brand-primary)]">
                        {g.guide_type}
                      </span>
                      <p className="mt-1 text-sm font-bold">{g.title}</p>
                    </div>
                    {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                  {isOpen && (
                    <div className="border-t border-[var(--border-subtle)] px-4 py-3">
                      <pre className="whitespace-pre-wrap font-sans text-xs leading-relaxed text-[var(--text-secondary)]">
                        {g.content_markdown}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {data.modules.length === 0 ? (
        <EmptyState title="Curso sin módulos publicados" description="El instructor aún está preparando el contenido." />
      ) : (
        <div className="space-y-4">
          {data.modules.map((mod) => (
            <section key={mod.id} className="surface-card p-5">
              <h2 className="text-lg font-bold">{mod.title}</h2>
              {mod.description && <p className="mt-1 text-sm text-[var(--text-secondary)]">{mod.description}</p>}
              <div className="mt-4 space-y-2.5">
                {mod.lessons.map((lesson) => {
                  const targetUrl = lesson.active_lesson_version_id
                    ? `/lessons/${lesson.active_lesson_version_id}${classroomId ? `?classroomId=${classroomId}` : ''}`
                    : null;
                  const isExam = lesson.lesson_type === 'strong_exam';
                  return (
                    <div
                      key={lesson.id}
                      className="flex flex-col gap-3 rounded-xl border border-[var(--border-subtle)] p-4 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-semibold text-sm">{lesson.title}</span>
                          {isExam && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-[11px] font-bold text-amber-950">
                              <Flame className="h-3 w-3 text-amber-600" /> Prueba Fuerte (Min {lesson.passing_score_pct ?? 85}%)
                            </span>
                          )}
                          {lesson.is_safety_critical && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-[11px] font-semibold text-red-900">
                              <ShieldAlert className="h-3 w-3" /> Crítica
                            </span>
                          )}
                        </div>
                        <p className="mt-1 flex items-center gap-2 text-xs text-[var(--text-secondary)]">
                          <Clock className="h-3.5 w-3.5" /> {lesson.estimated_minutes} min
                          {lesson.active_version_number ? ` • v${lesson.active_version_number}` : ' • Borrador'}
                        </p>
                      </div>
                      {targetUrl ? (
                        <Link
                          to={targetUrl}
                          className="btn-primary inline-flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-semibold"
                        >
                          <Play className="h-3.5 w-3.5" /> {isExam ? 'Rendir Prueba Fuerte' : 'Iniciar lección'}
                        </Link>
                      ) : (
                        <span className="text-xs text-[var(--text-secondary)]">No publicada</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
