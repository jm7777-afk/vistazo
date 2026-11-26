import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Heart, Layers, Zap } from 'lucide-react';
import { EmptyState, ErrorBanner, LoadingState } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { LibraryItem } from '../types/api';

const API_ORIGIN = (import.meta.env.VITE_API_URL ?? '/api/v1').replace(/\/api\/v1$/, '');

export function VisualLibraryPage() {
  const { user } = useAppState();
  const queryClient = useQueryClient();
  const [flashIndex, setFlashIndex] = useState<number | null>(null);

  const libraryQuery = useQuery({
    queryKey: ['my-visual-library'],
    queryFn: () => apiRequest<LibraryItem[]>('/library/me'),
    enabled: Boolean(user),
  });

  const flashMutation = useMutation({
    mutationFn: ({ assetId, toggleFavorite }: { assetId: string; toggleFavorite?: boolean }) =>
      apiRequest<LibraryItem>(
        `/library/flash-review/${assetId}${
          toggleFavorite !== undefined ? `?toggle_favorite=${String(toggleFavorite)}` : ''
        }`,
        { method: 'POST' }
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['my-visual-library'] });
    },
  });

  if (!user) {
    return <EmptyState title="Biblioteca Visual" description="Inicia sesión para desbloquear tarjetas y diagramas." />;
  }
  if (libraryQuery.isLoading) return <LoadingState label="Cargando biblioteca visual..." />;
  if (libraryQuery.error) return <ErrorBanner message={(libraryQuery.error as Error).message} />;

  const items = libraryQuery.data ?? [];
  const flashItem = flashIndex !== null ? items[flashIndex] : null;

  return (
    <div className="space-y-6">
      <div className="surface-card flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold">
            <Layers className="h-5 w-5 text-[var(--brand-primary)]" /> Biblioteca Visual Personal
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Recursos desbloqueados al completar lecciones, listos para Entrenamiento Flash móvil.
          </p>
        </div>
        {items.length > 0 && (
          <button
            type="button"
            onClick={() => setFlashIndex(0)}
            className="btn-primary inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold"
          >
            <Zap className="h-4 w-4" /> Modo Entrenamiento Flash
          </button>
        )}
      </div>

      {flashItem && (
        <div className="surface-card border-2 border-[var(--brand-primary)] p-6 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[var(--brand-primary)]">
              Entrenamiento Flash ({flashIndex! + 1}/{items.length})
            </span>
            <button
              type="button"
              onClick={() => setFlashIndex(null)}
              className="text-xs font-semibold text-[var(--text-secondary)] underline"
            >
              Cerrar modo flash
            </button>
          </div>
          <img
            src={`${API_ORIGIN}${flashItem.signed_url}`}
            alt={flashItem.title}
            loading="lazy"
            className="mx-auto max-h-60 rounded-xl border border-[var(--border-subtle)] object-contain"
          />
          <div>
            <h2 className="text-lg font-bold">{flashItem.title}</h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">{flashItem.description}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => {
                flashMutation.mutate({ assetId: flashItem.asset_id });
                setFlashIndex((prev) => (prev !== null && prev + 1 < items.length ? prev + 1 : 0));
              }}
              className="btn-primary px-4 py-2 text-xs font-semibold"
            >
              Recordado → Siguiente tarjeta
            </button>
            <button
              type="button"
              onClick={() =>
                flashMutation.mutate({ assetId: flashItem.asset_id, toggleFavorite: !flashItem.is_favorite })
              }
              className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-xs font-semibold"
            >
              <Heart className={`h-4 w-4 ${flashItem.is_favorite ? 'fill-red-500 text-red-500' : ''}`} />
              {flashItem.is_favorite ? 'Favorito' : 'Marcar favorito'}
            </button>
          </div>
        </div>
      )}

      {items.length === 0 ? (
        <EmptyState
          title="Tu biblioteca está vacía"
          description="Completa una lección con recursos multimedia asociados para desbloquear tarjetas aquí."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <article key={item.library_item_id} className="surface-card flex flex-col justify-between p-4">
              <div>
                <img
                  src={`${API_ORIGIN}${item.signed_url}`}
                  alt={item.title}
                  loading="lazy"
                  className="mb-3 h-36 w-full rounded-lg border border-[var(--border-subtle)] object-cover"
                />
                <h2 className="font-bold text-sm">{item.title}</h2>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">{item.description}</p>
              </div>
              <div className="mt-3 flex items-center justify-between text-[11px] text-[var(--text-secondary)]">
                <span>Repasos flash: {item.flash_reviews_count}</span>
                <span>{item.tags.slice(0, 2).join(' · ')}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
