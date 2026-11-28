import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Compass, HeartHandshake, HelpCircle, Palette, Radio, School, Sparkles, Wand2, X } from 'lucide-react';
import { useAppState } from '../../stores/AppContext';
import type { UIProfile } from '../../types/api';

const PROFILES: { id: UIProfile; label: string; desc: string }[] = [
  { id: 'pro', label: 'Profesional', desc: 'Tono sobrio y técnico' },
  { id: 'youth', label: 'Juvenil', desc: 'Dinámico y vibrante' },
  { id: 'kids', label: 'Infantil', desc: 'Cálido y botones grandes' },
];

export function QuickHelpFab() {
  const [open, setOpen] = useState(false);
  const { user, activeOrg, uiProfile, setUiProfile } = useAppState();

  const isEducator = Boolean(
    user?.is_super_admin ||
      user?.account_type === 'educator' ||
      (activeOrg && ['instructor', 'coordinator'].includes(activeOrg.role_code))
  );

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Abrir guía rápida de uso"
        className="fixed bottom-20 right-4 z-30 inline-flex items-center gap-2 rounded-full border border-[var(--border-subtle)] bg-[var(--brand-primary)] px-4 py-2.5 text-xs font-bold text-white shadow-lg transition hover:-translate-y-0.5 hover:brightness-110 md:bottom-6 md:right-6"
      >
        {open ? <X className="h-4 w-4" /> : <HelpCircle className="h-4 w-4" />}
        <span className="hidden sm:inline">{open ? 'Cerrar guía' : '¿Cómo funciona?'}</span>
      </button>

      {open && (
        <aside
          aria-label="Guía rápida interactiva"
          className="surface-card vzt-pop fixed bottom-34 right-4 z-30 w-[calc(100vw-2rem)] max-w-sm p-5 shadow-2xl md:bottom-20 md:right-6"
        >
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
            <span className="flex items-center gap-1.5 text-sm font-extrabold text-[var(--brand-primary)]">
              <Sparkles className="h-4 w-4" /> Guía Rápida Vistazo
            </span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-lg p-1 text-[var(--text-secondary)] hover:bg-slate-100"
              aria-label="Cerrar"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <p className="mt-3 text-xs text-[var(--text-secondary)]">
            Atajos directos según lo que quieras hacer ahora:
          </p>

          <div className="mt-3 space-y-2">
            <Link
              to="/catalog"
              onClick={() => setOpen(false)}
              className="interactive-card flex items-center gap-2.5 rounded-xl border border-[var(--border-subtle)] bg-white p-2.5 text-xs"
            >
              <Compass className="h-4 w-4 text-[var(--brand-primary)]" />
              <div>
                <p className="font-bold">Explorar Cursos Gratis</p>
                <p className="text-[11px] text-[var(--text-secondary)]">Empieza cualquier lección de 5 min</p>
              </div>
            </Link>

            <Link
              to="/unirse"
              onClick={() => setOpen(false)}
              className="interactive-card flex items-center gap-2.5 rounded-xl border border-[var(--border-subtle)] bg-white p-2.5 text-xs"
            >
              <School className="h-4 w-4 text-emerald-600" />
              <div>
                <p className="font-bold">Unirme con Código VZT</p>
                <p className="text-[11px] text-[var(--text-secondary)]">Entra a tu salón o escanea un QR</p>
              </div>
            </Link>

            <Link
              to="/vivo"
              onClick={() => setOpen(false)}
              className="interactive-card flex items-center gap-2.5 rounded-xl border border-[var(--border-subtle)] bg-white p-2.5 text-xs"
            >
              <Radio className="h-4 w-4 text-indigo-600" />
              <div>
                <p className="font-bold">Entrar a Clase en Vivo</p>
                <p className="text-[11px] text-[var(--text-secondary)]">Participa en un quiz en tiempo real</p>
              </div>
            </Link>

            {isEducator ? (
              <Link
                to="/studio"
                onClick={() => setOpen(false)}
                className="interactive-card flex items-center gap-2.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-accent-soft)]/50 p-2.5 text-xs"
              >
                <Wand2 className="h-4 w-4 text-[var(--brand-primary)]" />
                <div>
                  <p className="font-bold">Ir a mi Estudio Docente IA</p>
                  <p className="text-[11px] text-[var(--text-secondary)]">Crea materias, retos y exámenes</p>
                </div>
              </Link>
            ) : (
              <Link
                to="/familia"
                onClick={() => setOpen(false)}
                className="interactive-card flex items-center gap-2.5 rounded-xl border border-[var(--border-subtle)] bg-white p-2.5 text-xs"
              >
                <HeartHandshake className="h-4 w-4 text-rose-600" />
                <div>
                  <p className="font-bold">Portal Familiar</p>
                  <p className="text-[11px] text-[var(--text-secondary)]">Consulta progreso con código familiar</p>
                </div>
              </Link>
            )}
          </div>

          <div className="mt-4 border-t border-[var(--border-subtle)] pt-3">
            <p className="mb-2 flex items-center gap-1.5 text-[11px] font-bold uppercase text-[var(--text-secondary)]">
              <Palette className="h-3.5 w-3.5 text-[var(--brand-primary)]" /> Estilo visual instantáneo
            </p>
            <div className="grid grid-cols-3 gap-1.5">
              {PROFILES.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setUiProfile(p.id)}
                  className={`rounded-lg border px-2 py-1.5 text-center text-[11px] font-bold transition ${
                    uiProfile === p.id
                      ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)] text-[var(--brand-primary)]'
                      : 'border-[var(--border-subtle)] bg-white text-[var(--text-secondary)] hover:bg-slate-50'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        </aside>
      )}
    </>
  );
}
