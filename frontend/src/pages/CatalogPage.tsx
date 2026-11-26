import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { BookOpen, Sparkles } from 'lucide-react';
import { EmptyState, ErrorBanner, LoadingState } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import type { CourseSummary } from '../types/api';

export function CatalogPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['public-catalog'],
    queryFn: () => apiRequest<CourseSummary[]>('/catalog/courses'),
  });

  if (isLoading) return <LoadingState label="Cargando catálogo público..." />;
  if (error) return <ErrorBanner message={(error as Error).message} onRetry={() => void refetch()} />;

  return (
    <div className="space-y-6">
      <section className="surface-card bg-[var(--bg-accent-soft)] p-6">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--brand-primary)]">
          <Sparkles className="h-4 w-4" /> Modo Estudio Libre
        </div>
        <h1 className="mt-2 text-2xl font-bold">Explora cursos públicos sin matrícula obligatoria</h1>
        <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
          Practica con lecciones interactivas de microlearning y guarda tu avance al iniciar sesión.
        </p>
      </section>

      {!data || data.length === 0 ? (
        <EmptyState
          title="No hay cursos públicos publicados"
          description="Pronto publicaremos nuevos cursos abiertos de estudio libre."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((course) => (
            <article key={course.id} className="surface-card flex flex-col justify-between p-5">
              <div>
                <span className="rounded-full bg-[var(--bg-accent-soft)] px-2.5 py-0.5 text-xs font-semibold text-[var(--brand-primary)]">
                  {course.education_level}
                </span>
                <h2 className="mt-3 text-lg font-bold">{course.title}</h2>
                <p className="mt-1.5 text-sm text-[var(--text-secondary)]">{course.description}</p>
              </div>
              <Link
                to={`/courses/${course.id}`}
                className="btn-primary mt-5 inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold"
              >
                <BookOpen className="h-4 w-4" /> Abrir curso
              </Link>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
