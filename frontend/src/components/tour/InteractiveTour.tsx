import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Compass,
  GraduationCap,
  Minimize2,
  MousePointerClick,
  Play,
  Presentation,
  Sparkles,
  X,
} from 'lucide-react';
import { useAppState } from '../../stores/AppContext';
import { AnimatedProgressBar, CelebrationBurst } from '../ui/MotionPrimitives';

export type TourTrack = 'student' | 'educator';

interface TourStep {
  id: string;
  route: string;
  target: string;
  title: string;
  description: string;
  actionPrompt: string;
}

interface TourContextValue {
  isOpen: boolean;
  track: TourTrack;
  startTour: (preferredTrack?: TourTrack) => void;
  closeTour: () => void;
}

const TourContext = createContext<TourContextValue | undefined>(undefined);

const TOUR_DONE_KEY = 'vistazo_tour_done_v1';

export function TourProvider({ children }: { children: React.ReactNode }) {
  const { user, activeOrg } = useAppState();
  const canAuthor = Boolean(
    user?.is_super_admin ||
      user?.account_type === 'educator' ||
      (activeOrg && ['instructor', 'coordinator'].includes(activeOrg.role_code))
  );

  const [isOpen, setIsOpen] = useState(false);
  const [track, setTrack] = useState<TourTrack>(canAuthor ? 'educator' : 'student');

  const startTour = useCallback(
    (preferredTrack?: TourTrack) => {
      setTrack(preferredTrack ?? (canAuthor ? 'educator' : 'student'));
      setIsOpen(true);
    },
    [canAuthor]
  );

  const closeTour = useCallback(() => {
    setIsOpen(false);
    localStorage.setItem(TOUR_DONE_KEY, '1');
  }, []);

  const value = useMemo(
    () => ({ isOpen, track, startTour, closeTour }),
    [isOpen, track, startTour, closeTour]
  );

  return (
    <TourContext.Provider value={value}>
      {children}
      {isOpen && (
        <InteractiveTourOverlay
          track={track}
          canAuthor={canAuthor}
          isSignedIn={Boolean(user)}
          onChangeTrack={setTrack}
          onClose={closeTour}
        />
      )}
    </TourContext.Provider>
  );
}

export function useInteractiveTour() {
  const ctx = useContext(TourContext);
  if (!ctx) throw new Error('useInteractiveTour must be used within TourProvider');
  return ctx;
}

function buildSteps(track: TourTrack, canAuthor: boolean, isSignedIn: boolean): TourStep[] {
  if (track === 'educator') {
    if (canAuthor) {
      return [
        {
          id: 'edu-stepper',
          route: '/studio',
          target: 'studio-stepper',
          title: 'Flujo del Estudio Docente (Pasos 1 al 7)',
          description:
            'Aquí tienes todo en orden: desde el Arquitecto IA inicial hasta retos, banco de preguntas y códigos QR.',
          actionPrompt: 'Haz clic en cualquiera de las 7 pestañas numeradas para explorar.',
        },
        {
          id: 'edu-workspace',
          route: '/studio',
          target: 'studio-workspace',
          title: 'Crea manual o asistido por IA',
          description:
            'Puedes subir un PDF/DOCX o escribir un tema y la IA organiza módulos, temarios y guías al instante.',
          actionPrompt: 'Interactúa o enfoca cualquier campo del panel de creación de arriba.',
        },
        {
          id: 'edu-plans',
          route: '/planes',
          target: 'billing-plans',
          title: 'Capacidad, Cuotas IA y Planes SaaS',
          description:
            'Administra cuántos estudiantes y generaciones con IA tiene habilitados tu organización o cátedra.',
          actionPrompt: 'Explora o haz clic sobre las tarjetas de planes disponibles.',
        },
      ];
    }
    return [
      {
        id: 'edu-register',
        route: '/register',
        target: 'register-role',
        title: 'Paso inicial para Educadores',
        description:
          'Al crear tu cuenta, elige "Soy Educador" para desbloquear tu propio Estudio Pedagógico IA y aulas.',
        actionPrompt: 'Toca la tarjeta "Soy Educador" arriba para ver cómo se configura tu espacio.',
      },
      {
        id: 'edu-plans-preview',
        route: '/planes',
        target: 'billing-plans',
        title: 'Escalabilidad Institucional',
        description:
          'Vistazo soporta desde un docente independiente hasta universidades con miles de alumnos y webhooks.',
        actionPrompt: 'Revisa los planes disponibles haciendo clic en una tarjeta.',
      },
    ];
  }

  return [
    {
      id: 'stu-demo',
      route: '/',
      target: 'hero-demo',
      title: 'Responde un reto en 30 segundos',
      description:
        'Cada microlección de Vistazo combina imágenes, explicaciones verificables y puntuación inmediata.',
      actionPrompt: 'Elige una opción (A, B o C) y pulsa "Comprobar respuesta al instante".',
    },
    {
      id: 'stu-profile',
      route: '/',
      target: 'profile-switcher',
      title: 'Adapta los colores y tamaño a tu gusto',
      description:
        'Cambia entre Infantil, Juvenil o Profesional en vivo; los botones y contrastes se ajustan al instante.',
      actionPrompt: 'Haz clic en cualquiera de los 3 perfiles visuales resaltados.',
    },
    {
      id: 'stu-catalog',
      route: '/catalog',
      target: 'catalog-filters',
      title: 'Busca y filtra cursos públicos gratis',
      description:
        'En Estudio Libre puedes practicar materias sin matrícula usando el buscador o las píldoras por nivel.',
      actionPrompt: 'Escribe una palabra en el buscador o toca un filtro de nivel educativo.',
    },
    {
      id: 'stu-join',
      route: '/unirse',
      target: 'join-code-box',
      title: 'Entra al salón de tu profesor',
      description:
        'Si tu docente comparte un código VZT o código QR, escríbelo aquí para unirte a su cohorte y ganar XP.',
      actionPrompt: 'Haz clic dentro del recuadro "VZT-XXXXXX" para probar cómo se ingresa.',
    },
    isSignedIn
      ? {
          id: 'stu-reviews',
          route: '/reviews',
          target: 'reviews-actions',
          title: 'Repaso SM-2 y Tarjetas 3D',
          description:
            'Aquí refuerzas lo aprendido justo antes de olvidarlo y practicas tus apuntes con Tarjetas 3D y CSV Anki.',
          actionPrompt: 'Toca uno de los botones resaltados para iniciar o explorar el repaso.',
        }
      : {
          id: 'stu-family',
          route: '/familia',
          target: 'family-code-form',
          title: 'Portal Seguro para Familias',
          description:
            'Padres y tutores pueden seguir XP, racha y lecciones completadas usando solo un código FAM sin exponer PII.',
          actionPrompt: 'Haz clic en el campo de código familiar para conocer cómo consultarlo.',
        },
  ];
}

function InteractiveTourOverlay({
  track,
  canAuthor,
  isSignedIn,
  onChangeTrack,
  onClose,
}: {
  track: TourTrack;
  canAuthor: boolean;
  isSignedIn: boolean;
  onChangeTrack: (t: TourTrack) => void;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const steps = useMemo(() => buildSteps(track, canAuthor, isSignedIn), [track, canAuthor, isSignedIn]);
  const [stepIdx, setStepIdx] = useState(0);
  const [completedIds, setCompletedIds] = useState<Record<string, boolean>>({});
  const [minimized, setMinimized] = useState(false);
  const [finished, setFinished] = useState(false);

  useEffect(() => {
    setStepIdx(0);
    setFinished(false);
  }, [track]);

  const currentStep = steps[Math.min(stepIdx, steps.length - 1)];

  // Navegar automáticamente a la ruta del paso actual
  useEffect(() => {
    if (finished || !currentStep) return;
    if (location.pathname !== currentStep.route) {
      navigate(currentStep.route);
    }
  }, [currentStep, finished, location.pathname, navigate]);

  // Resaltar elemento real y detectar interacción del usuario
  useEffect(() => {
    if (finished || !currentStep) return;
    let cleanedUp = false;
    let activeEl: HTMLElement | null = null;

    const markDone = () => {
      setCompletedIds((prev) => ({ ...prev, [currentStep.id]: true }));
    };

    const attach = () => {
      if (cleanedUp) return false;
      const el = document.querySelector<HTMLElement>(`[data-tour="${currentStep.target}"]`);
      if (!el) return false;
      activeEl = el;
      el.classList.add('vzt-tour-highlight');
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.addEventListener('click', markDone);
      el.addEventListener('input', markDone);
      el.addEventListener('focusin', markDone);
      return true;
    };

    let timer: number | undefined;
    if (!attach()) {
      timer = window.setInterval(() => {
        if (attach() && timer !== undefined) {
          window.clearInterval(timer);
        }
      }, 150);
    }

    return () => {
      cleanedUp = true;
      if (timer !== undefined) window.clearInterval(timer);
      if (activeEl) {
        activeEl.classList.remove('vzt-tour-highlight');
        activeEl.removeEventListener('click', markDone);
        activeEl.removeEventListener('input', markDone);
        activeEl.removeEventListener('focusin', markDone);
      }
    };
  }, [currentStep, finished, location.pathname]);

  if (minimized) {
    return (
      <button
        type="button"
        onClick={() => setMinimized(false)}
        className="vzt-pop fixed bottom-20 left-4 z-40 inline-flex items-center gap-2 rounded-full border border-[var(--brand-primary)] bg-white px-4 py-2 text-xs font-extrabold text-[var(--brand-primary)] shadow-xl md:bottom-6 md:left-6"
      >
        <Play className="h-3.5 w-3.5 fill-current" />
        Reanudar Guía ({stepIdx + 1}/{steps.length})
      </button>
    );
  }

  const isStepDone = Boolean(completedIds[currentStep?.id]);
  const doneCount = steps.filter((s) => completedIds[s.id]).length;
  const pct = finished ? 100 : Math.round(((stepIdx + (isStepDone ? 1 : 0)) / steps.length) * 100);

  return (
    <aside
      aria-label="Guía interactiva paso a paso"
      className="surface-card vzt-pop fixed bottom-20 left-4 z-40 w-[calc(100vw-2rem)] max-w-md border-2 border-[var(--brand-primary)]/40 bg-white/98 p-4 shadow-2xl backdrop-blur-md md:bottom-6 md:left-6"
    >
      {/* Cabecera con selector de ruta Estudiante / Educador */}
      <div className="flex items-center justify-between gap-2 border-b border-[var(--border-subtle)] pb-2.5">
        <div className="flex items-center gap-1.5">
          <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-[var(--brand-primary)] text-white">
            <Compass className="h-3.5 w-3.5" />
          </span>
          <span className="text-xs font-extrabold text-[var(--brand-primary)]">
            Guía Interactiva en Vivo
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setMinimized(true)}
            aria-label="Minimizar guía"
            className="rounded-lg p-1 text-[var(--text-secondary)] hover:bg-slate-100"
          >
            <Minimize2 className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar guía"
            className="rounded-lg p-1 text-[var(--text-secondary)] hover:bg-slate-100"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Selector de recorrido */}
      <div className="mt-2.5 grid grid-cols-2 gap-1.5">
        <button
          type="button"
          onClick={() => onChangeTrack('student')}
          className={`flex items-center justify-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-bold transition ${
            track === 'student'
              ? 'bg-[var(--brand-primary)] text-white'
              : 'bg-slate-100 text-[var(--text-secondary)] hover:bg-slate-200'
          }`}
        >
          <GraduationCap className="h-3.5 w-3.5" /> Ruta Estudiante
        </button>
        <button
          type="button"
          onClick={() => onChangeTrack('educator')}
          className={`flex items-center justify-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-bold transition ${
            track === 'educator'
              ? 'bg-[var(--brand-primary)] text-white'
              : 'bg-slate-100 text-[var(--text-secondary)] hover:bg-slate-200'
          }`}
        >
          <Presentation className="h-3.5 w-3.5" /> Ruta Educador
        </button>
      </div>

      <div className="mt-3">
        <AnimatedProgressBar
          percent={pct}
          label={finished ? '¡Recorrido completado!' : `Paso ${stepIdx + 1} de ${steps.length} • ${doneCount} probados`}
          tone={finished || isStepDone ? 'emerald' : 'brand'}
        />
      </div>

      {finished ? (
        <div className="vzt-pop mt-4 space-y-3 rounded-xl bg-emerald-50 p-4 text-center">
          <div className="flex justify-center">
            <CelebrationBurst active badgeText="¡Dominado!" />
          </div>
          <p className="text-sm font-extrabold text-emerald-950">
            ¡Ya sabes usar Vistazo paso a paso!
          </p>
          <p className="text-xs text-emerald-900">
            Puedes volver a abrir esta guía en cualquier momento desde el botón superior <strong>Tour guiado</strong> o desde{' '}
            <strong>¿Cómo funciona?</strong>.
          </p>
          <button type="button" onClick={onClose} className="btn-primary w-full py-2 text-xs font-bold">
            Empezar a usar la plataforma
          </button>
        </div>
      ) : (
        <div className="mt-3 space-y-3">
          <div>
            <h3 className="text-sm font-extrabold text-[var(--text-primary)]">{currentStep.title}</h3>
            <p className="mt-1 text-xs leading-relaxed text-[var(--text-secondary)]">
              {currentStep.description}
            </p>
          </div>

          <div
            className={`rounded-xl border p-2.5 text-xs transition ${
              isStepDone
                ? 'vzt-pop border-emerald-300 bg-emerald-50 text-emerald-950'
                : 'border-amber-300 bg-amber-50/90 text-amber-950'
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-start gap-2">
                {isStepDone ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                ) : (
                  <MousePointerClick className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 animate-bounce" />
                )}
                <div>
                  <p className="font-bold">
                    {isStepDone ? '¡Excelente, ya lo probaste!' : 'Tu turno — Pruébalo en pantalla:'}
                  </p>
                  <p className="mt-0.5 leading-snug">{currentStep.actionPrompt}</p>
                </div>
              </div>
              {isStepDone && <CelebrationBurst active badgeText="✓" />}
            </div>
          </div>

          <div className="flex items-center justify-between gap-2 pt-1">
            <button
              type="button"
              disabled={stepIdx === 0}
              onClick={() => setStepIdx((i) => Math.max(0, i - 1))}
              className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:bg-slate-50 disabled:opacity-40"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Anterior
            </button>

            <div className="flex items-center gap-2">
              {!isStepDone && (
                <button
                  type="button"
                  onClick={() => setCompletedIds((prev) => ({ ...prev, [currentStep.id]: true }))}
                  className="text-[11px] font-semibold text-[var(--brand-primary)] underline"
                >
                  Marcar visto
                </button>
              )}
              {stepIdx < steps.length - 1 ? (
                <button
                  type="button"
                  onClick={() => setStepIdx((i) => i + 1)}
                  className="btn-primary inline-flex items-center gap-1 px-4 py-1.5 text-xs font-bold"
                >
                  Siguiente <ArrowRight className="h-3.5 w-3.5" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setFinished(true)}
                  className="btn-primary inline-flex items-center gap-1 px-4 py-1.5 text-xs font-bold"
                >
                  <Sparkles className="h-3.5 w-3.5" /> Finalizar guía
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
