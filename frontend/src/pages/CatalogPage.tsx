import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ArrowRight, BookOpen, Filter, Search, Sparkles } from 'lucide-react';
import { EmptyState, ErrorBanner, LoadingState } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import type { CourseSummary } from '../types/api';

const LEVEL_FILTERS = [
  { id: 'all', label: 'Todos' },
  { id: 'primary', label: 'Primaria' },
  { id: 'secondary', label: 'Secundaria' },
  { id: 'high_school', label: 'Bachillerato' },
  { id: 'university', label: 'Universidad' },
  { id: 'technical', label: 'Técnico' },
  { id: 'rescue', label: 'Rescate' },
];

export function CatalogPage() {
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState('all');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['public-catalog'],
    queryFn: () => apiRequest<CourseSummary[]>('/catalog/courses'),
  });

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (data ?? []).filter((c) => {
      const matchesLevel = levelFilter === 'all' || c.education_level === levelFilter;
      const matchesSearch =
        !q || c.title.toLowerCase().includes(q) || (c.description ?? '').toLowerCase().includes(q);
      return matchesLevel && matchesSearch;
    });
  }, [data, search, levelFilter]);

  if (isLoading) return <LoadingState label="Cargando catálogo público..." />;
  if (error) return <ErrorBanner message={(error as Error).message} onRetry={() => void refetch()} />;

  return (
    <div className="space-y-6">
      <section className="surface-card relative overflow-hidden bg-gradient-to-br from-[var(--bg-surface)] to-[var(--bg-accent-soft)] p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--brand-primary)]">
              <Sparkles className="h-4 w-4" /> Modo Estudio Libre
            </div>
            <h1 className="mt-2 text-2xl font-bold">Explora cursos públicos sin matrícula obligatoria</h1>
            <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
              Elige cualquier materia, aprende con retos visuales de 5 minutos y guarda tu progreso al iniciar sesión.
            </p>
          </div>
          <img
            src="/brand/vistazo-icon.png"
            alt="Emblema Vistazo"
            className="vzt-float hidden h-16 w-auto shrink-0 object-contain sm:block"
          />
        </div>

        {/* Barra de búsqueda y filtros por nivel */}
        <div className="mt-5 space-y-3 border-t border-[var(--border-subtle)]/70 pt-4">
          <div className="relative max-w-md">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-[var(--text-secondary)]" />
            <input
              type="search"
              placeholder="Buscar curso o tema..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-xl border border-[var(--border-subtle)] bg-white py-2 pl-9 pr-3 text-sm"
            />
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--text-secondary)] mr-1">
              <Filter className="h-3.5 w-3.5" /> Nivel:
            </span>
            {LEVEL_FILTERS.map((lvl) => (
              <button
                key={lvl.id}
                type="button"
                onClick={() => setLevelFilter(lvl.id)}
                className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                  levelFilter === lvl.id
                    ? 'bg-[var(--brand-primary)] text-white shadow-xs'
                    : 'border border-[var(--border-subtle)] bg-white text-[var(--text-secondary)] hover:bg-slate-50'
                }`}
              >
                {lvl.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {filtered.length === 0 ? (
        <EmptyState
          title="No encontramos cursos con ese filtro"
          description="Prueba limpiando el buscador o seleccionando 'Todos' los niveles educativos."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((course) => (
            <article key={course.id} className="surface-card interactive-card flex flex-col justify-between p-5">
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className="rounded-full bg-[var(--bg-accent-soft)] px-2.5 py-0.5 text-xs font-bold text-[var(--brand-primary)]">
                    {course.education_level}
                  </span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-[var(--text-secondary)]">
                    {course.ui_profile}
                  </span>
                </div>
                <h2 className="mt-3 text-lg font-bold">{course.title}</h2>
                <p className="mt-1.5 text-sm text-[var(--text-secondary)] line-clamp-3">{course.description}</p>
              </div>
              <Link
                to={`/courses/${course.id}`}
                className="btn-primary mt-5 inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold"
              >
                <BookOpen className="h-4 w-4" /> Abrir curso <ArrowRight className="h-4 w-4" />
              </Link>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
