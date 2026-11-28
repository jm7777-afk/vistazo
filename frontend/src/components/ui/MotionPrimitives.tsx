import { useEffect, useState, type CSSProperties } from 'react';
import { HelpCircle, Sparkles } from 'lucide-react';

const CONFETTI_VECTORS = [
  { tx: '-54px', ty: '-42px', color: '#10b981' },
  { tx: '-26px', ty: '-60px', color: '#f59e0b' },
  { tx: '0px', ty: '-66px', color: '#0ea5e9' },
  { tx: '28px', ty: '-58px', color: '#8b5cf6' },
  { tx: '56px', ty: '-40px', color: '#ec4899' },
  { tx: '-40px', ty: '-22px', color: '#22c55e' },
  { tx: '42px', ty: '-20px', color: '#f97316' },
];

export function CelebrationBurst({
  active,
  badgeText = '+XP',
}: {
  active: boolean;
  badgeText?: string;
}) {
  if (!active) return null;

  return (
    <div className="pointer-events-none relative inline-flex items-center justify-center" aria-hidden="true">
      {CONFETTI_VECTORS.map((vec, idx) => (
        <span
          key={idx}
          className="vzt-confetti-dot absolute h-2 w-2 rounded-full"
          style={
            {
              backgroundColor: vec.color,
              '--tx': vec.tx,
              '--ty': vec.ty,
            } as CSSProperties
          }
        />
      ))}
      <span className="vzt-pop inline-flex items-center gap-1 rounded-full bg-emerald-600 px-2.5 py-0.5 text-[11px] font-extrabold text-white shadow-sm">
        <Sparkles className="h-3 w-3" /> {badgeText}
      </span>
    </div>
  );
}

export function AnimatedProgressBar({
  percent,
  label,
  tone = 'brand',
}: {
  percent: number;
  label?: string;
  tone?: 'brand' | 'emerald' | 'amber';
}) {
  const clamped = Math.max(0, Math.min(100, Math.round(percent)));
  const bg =
    tone === 'emerald'
      ? 'bg-emerald-600'
      : tone === 'amber'
        ? 'bg-amber-500'
        : 'bg-[var(--brand-primary)]';

  return (
    <div className="space-y-1">
      {label && (
        <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
          <span>{label}</span>
          <span className="font-bold text-[var(--text-primary)]">{clamped}%</span>
        </div>
      )}
      <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200/80 p-0.5">
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${bg} ${
            clamped > 0 && clamped < 100 ? 'vzt-progress-bar' : ''
          }`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}

export function AnimatedNumber({ value, suffix = '' }: { value: number; suffix?: string }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const target = Math.max(0, Math.round(value));
    if (target === 0) {
      setDisplay(0);
      return;
    }
    const steps = 16;
    let frame = 0;
    const id = window.setInterval(() => {
      frame += 1;
      const ratio = frame / steps;
      const eased = 1 - Math.pow(1 - ratio, 3);
      setDisplay(Math.round(target * eased));
      if (frame >= steps) {
        setDisplay(target);
        window.clearInterval(id);
      }
    }, 24);
    return () => window.clearInterval(id);
  }, [value]);

  return (
    <span>
      {display}
      {suffix}
    </span>
  );
}

export function QuickGuideBanner({
  title,
  steps,
}: {
  title: string;
  steps: { num: string; text: string }[];
}) {
  return (
    <div className="vzt-fade-up rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-accent-soft)]/60 p-4">
      <p className="mb-2.5 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-[var(--brand-primary)]">
        <HelpCircle className="h-4 w-4" /> {title}
      </p>
      <div className="grid gap-2 sm:grid-cols-3">
        {steps.map((s) => (
          <div
            key={s.num}
            className="flex items-start gap-2.5 rounded-xl bg-white/85 p-2.5 text-xs shadow-xs"
          >
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--brand-primary)] text-[11px] font-extrabold text-white">
              {s.num}
            </span>
            <span className="leading-snug text-[var(--text-secondary)]">{s.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
