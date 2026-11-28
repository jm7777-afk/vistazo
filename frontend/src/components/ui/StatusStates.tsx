import { AlertTriangle, CheckCircle2, Inbox, Sparkles } from 'lucide-react';

export function LoadingState({ label = 'Cargando...' }: { label?: string }) {
  return (
    <div className="surface-card vzt-fade-up flex flex-col items-center justify-center gap-4 p-8 text-center" role="status">
      <div className="relative flex h-14 w-14 items-center justify-center">
        <span className="absolute inset-0 animate-ping rounded-full bg-[var(--brand-primary)]/20" />
        <span className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--bg-accent-soft)] text-[var(--brand-primary)] shadow-sm">
          <Sparkles className="h-6 w-6 animate-pulse" />
        </span>
      </div>
      <p className="text-sm font-semibold text-[var(--text-primary)]">{label}</p>
      <div className="w-full max-w-sm space-y-2 pt-1" aria-hidden="true">
        <div className="vzt-skeleton h-3 w-full rounded-full" />
        <div className="vzt-skeleton mx-auto h-3 w-4/5 rounded-full" />
      </div>
    </div>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="vzt-shake flex flex-col gap-3 rounded-xl border border-red-300 bg-red-50 p-4 text-red-900 shadow-xs sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
        <p className="text-sm font-medium">{message}</p>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-lg border border-red-400 bg-white px-3 py-1.5 text-xs font-semibold text-red-800 transition hover:bg-red-100"
        >
          Reintentar
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="surface-card vzt-fade-up flex flex-col items-center justify-center p-8 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--bg-accent-soft)] text-[var(--brand-primary)]">
        <Inbox className="h-6 w-6" />
      </div>
      <h3 className="text-base font-bold">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-[var(--text-secondary)]">{description}</p>
    </div>
  );
}

export function SuccessBanner({ message }: { message: string }) {
  return (
    <div className="vzt-pop flex items-center gap-2.5 rounded-xl border border-emerald-300 bg-emerald-50 p-3.5 text-emerald-900 shadow-xs">
      <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />
      <p className="text-sm font-semibold">{message}</p>
    </div>
  );
}
