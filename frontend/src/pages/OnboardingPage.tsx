import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, Compass, Layers, Sparkles, Timer, Wand2 } from 'lucide-react';
import { AnimatedProgressBar } from '../components/ui/MotionPrimitives';
import { ErrorBanner } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { UIProfile, UserSummary } from '../types/api';

export function OnboardingPage() {
  const { user, uiProfile, setUiProfile, updateUser } = useAppState();
  const navigate = useNavigate();

  const isEducator = user?.account_type === 'educator' || Boolean(user?.is_super_admin);

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [goalMode, setGoalMode] = useState<'free' | 'rescue' | 'school' | 'ai_studio' | 'manual_studio'>(
    isEducator ? 'ai_studio' : user?.memberships.length ? 'rescue' : 'free'
  );
  const [dailyMinutes, setDailyMinutes] = useState<number>(user?.daily_goal_minutes ?? (isEducator ? 15 : 5));

  const saveMutation = useMutation({
    mutationFn: () =>
      apiRequest<UserSummary>('/auth/me/preferences', {
        method: 'PATCH',
        body: JSON.stringify({
          preferred_ui_profile: uiProfile,
          daily_goal_minutes: dailyMinutes,
          onboarding_completed: true,
        }),
      }),
    onSuccess: (updated) => {
      updateUser(updated);
      if (isEducator) {
        navigate('/studio');
        return;
      }
      navigate(goalMode === 'free' && !updated.memberships.length ? '/catalog' : '/dashboard');
    },
  });

  if (!user) {
    return null;
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div className="surface-card p-6 space-y-5">
        <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
          <span className="flex items-center gap-1.5 text-[var(--brand-primary)]">
            <Sparkles className="h-4 w-4" />{' '}
            {isEducator ? 'Configuración de Estudio Pedagógico' : 'Configuración inicial guiada'}
          </span>
          <span>Paso {step} de 3</span>
        </div>

        <AnimatedProgressBar percent={(step / 3) * 100} />

        {saveMutation.error && <ErrorBanner message={(saveMutation.error as Error).message} />}

        {step === 1 && (
          <div className="vzt-scale-in space-y-4">
            <h1 className="text-xl font-bold">
              {isEducator
                ? `¡Bienvenido, Prof. ${user.full_name}! ¿Cómo prefieres construir tu contenido?`
                : `¡Bienvenido, ${user.full_name}! ¿Cuál es tu enfoque principal?`}
            </h1>
            <div className="space-y-2.5">
              {(isEducator
                ? [
                    {
                      id: 'ai_studio' as const,
                      title: 'Arquitecto IA + Carga de Temarios',
                      desc: 'Sube o pega tus guías y la IA organiza módulos, metodología, pruebas fuertes e imágenes dinámicas.',
                    },
                    {
                      id: 'manual_studio' as const,
                      title: 'Autoría Manual Precisa (CRUD Total)',
                      desc: 'Crea paso a paso materias, nodos, retos, temarios y diagramas con control absoluto.',
                    },
                  ]
                : [
                    {
                      id: 'rescue' as const,
                      title: 'Brigada de Rescate / Capacitación Técnica',
                      desc: 'Protocolos críticos con refresco periódico de 45 días.',
                    },
                    {
                      id: 'school' as const,
                      title: 'Colegio, Bachillerato o Universidad',
                      desc: 'Aulas oficiales, pensums y certificaciones.',
                    },
                    {
                      id: 'free' as const,
                      title: 'Estudio Libre a mi ritmo',
                      desc: 'Explora cursos públicos gratuitos sin matrícula.',
                    },
                  ]
              ).map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => {
                    setGoalMode(opt.id);
                    if (opt.id === 'rescue') setUiProfile('pro');
                  }}
                  className={`w-full rounded-xl border p-4 text-left ${
                    goalMode === opt.id
                      ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)]'
                      : 'border-[var(--border-subtle)] bg-white'
                  }`}
                >
                  <p className="font-bold text-sm">{opt.title}</p>
                  <p className="text-xs text-[var(--text-secondary)]">{opt.desc}</p>
                </button>
              ))}
            </div>
            <button type="button" onClick={() => setStep(2)} className="btn-primary w-full py-2.5 text-sm font-semibold">
              Continuar
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="vzt-scale-in space-y-4">
            <h1 className="flex items-center gap-2 text-xl font-bold">
              <Layers className="h-5 w-5 text-[var(--brand-primary)]" />{' '}
              {isEducator ? 'Perfil visual de tus cursos y meta de trabajo' : 'Elige tu perfil visual y meta diaria'}
            </h1>
            <div className="grid gap-2.5 sm:grid-cols-3">
              {(
                [
                  { id: 'kids', label: 'Infantil' },
                  { id: 'youth', label: 'Juvenil' },
                  { id: 'pro', label: 'Profesional' },
                ] as { id: UIProfile; label: string }[]
              ).map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setUiProfile(p.id)}
                  className={`rounded-xl border p-3 text-center text-sm font-bold ${
                    uiProfile === p.id
                      ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)] text-[var(--brand-primary)]'
                      : 'border-[var(--border-subtle)] bg-white'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            <div className="pt-2">
              <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold">
                <Timer className="h-4 w-4 text-[var(--brand-primary)]" />{' '}
                {isEducator ? 'Meta diaria de diseño o repaso' : 'Meta diaria de microlearning'}
              </p>
              <div className="grid grid-cols-3 gap-2.5">
                {[5, 10, 15].map((mins) => (
                  <button
                    key={mins}
                    type="button"
                    onClick={() => setDailyMinutes(mins)}
                    className={`rounded-xl border p-3 text-center text-sm font-bold ${
                      dailyMinutes === mins
                        ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)] text-[var(--brand-primary)]'
                        : 'border-[var(--border-subtle)] bg-white'
                    }`}
                  >
                    {mins} min/día
                  </button>
                ))}
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-sm font-semibold"
              >
                Atrás
              </button>
              <button type="button" onClick={() => setStep(3)} className="btn-primary flex-1 py-2.5 text-sm font-semibold">
                Siguiente
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="vzt-scale-in space-y-4">
            <h1 className="flex items-center gap-2 text-xl font-bold">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />{' '}
              {isEducator
                ? '¡Tu Estudio Pedagógico está listo para crear!'
                : `¡Todo listo para tu primera misión de ${dailyMinutes} min!`}
            </h1>
            <div className="rounded-xl bg-[var(--bg-accent-soft)] p-4 text-sm space-y-1.5">
              <p>
                <strong>Rol activo:</strong> {isEducator ? 'Educador / Autor' : 'Estudiante'}
              </p>
              <p>
                <strong>Perfil visual:</strong> {uiProfile}
              </p>
              <p>
                <strong>Herramientas listas:</strong>{' '}
                {isEducator
                  ? 'CRUD de materias, nodos, guías, pruebas fuertes, imágenes dinámicas SVG y Asistente IA.'
                  : 'Micro-retos adaptativos, biblioteca visual y repaso espaciado SM-2.'}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-sm font-semibold"
              >
                Atrás
              </button>
              <button
                type="button"
                disabled={saveMutation.isPending}
                onClick={() => saveMutation.mutate()}
                className="btn-primary flex-1 inline-flex items-center justify-center gap-2 py-2.5 text-sm font-bold"
              >
                {isEducator ? <Wand2 className="h-4 w-4" /> : <Compass className="h-4 w-4" />}
                {saveMutation.isPending
                  ? 'Guardando...'
                  : isEducator
                    ? 'Abrir Estudio Pedagógico'
                    : 'Empezar ahora'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
