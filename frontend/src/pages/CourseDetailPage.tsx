import { useQuery } from '@tanstack/react-query';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { Clock, Play, ShieldAlert } from 'lucide-react';
import { EmptyState, ErrorBanner, LoadingState } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import type { CourseDetail } from '../types/api';

export function CourseDetailPage() {
  const { courseId } = useParams<{ courseId: string }>();
  const [searchParams] = useSearchParams();
  const classroomId = searchParams.get('classroomId');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['course-detail', courseId],
    queryFn: () => apiRequest<CourseDetail>(`/courses/${courseId}`),
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
                  return (
                    <div
                      key={lesson.id}
                      className="flex flex-col gap-3 rounded-xl border border-[var(--border-subtle)] p-4 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-semibold text-sm">{lesson.title}</span>
                          {lesson.is_safety_critical && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-900">
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
                          <Play className="h-3.5 w-3.5" /> Iniciar lección
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
