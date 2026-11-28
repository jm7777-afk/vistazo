import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Award,
  Brain,
  CheckCircle2,
  Compass,
  GraduationCap,
  HeartHandshake,
  Layers,
  Radio,
  School,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Wand2,
  WifiOff,
  XCircle,
} from 'lucide-react';
import { CelebrationBurst, QuickGuideBanner } from '../components/ui/MotionPrimitives';
import { useAppState } from '../stores/AppContext';
import type { UIProfile } from '../types/api';

const DEMO_OPTIONS = [
  { id: 'a', text: 'Movilizar al paciente de inmediato sin revisar el entorno' },
  { id: 'b', text: 'Asegurar la escena, usar EPP y estabilizar columna si hay trauma' },
  { id: 'c', text: 'Dar agua antes de evaluar el estado de conciencia' },
];

export function LandingPage() {
  const { user, uiProfile, setUiProfile } = useAppState();
  const navigate = useNavigate();
  const [demoAnswer, setDemoAnswer] = useState<string>('');
  const [demoSubmitted, setDemoSubmitted] = useState(false);
  const [verifyHash, setVerifyHash] = useState('');

  const profileSamples: { id: UIProfile; title: string; subtitle: string; badge: string }[] = [
    { id: 'kids', title: 'Infantil y Primaria', subtitle: 'Botones amplios y tonos cálidos', badge: '6-11 años' },
    { id: 'youth', title: 'Juvenil y Secundaria', subtitle: 'Dinámico, visual y ágil', badge: '12-17 años' },
    { id: 'pro', title: 'Profesional y Rescate', subtitle: 'Sobrio, técnico y preciso', badge: 'Uni / Técnico' },
  ];

  const isDemoCorrect = demoAnswer === 'b';

  return (
    <div className="space-y-10">
      {/* Hero animado con profundidad visual y vista previa interactiva en vivo */}
      <section className="surface-card relative overflow-hidden bg-gradient-to-br from-[var(--bg-surface)] via-[var(--bg-surface)] to-[var(--bg-accent-soft)] p-6 sm:p-10">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-[var(--brand-primary)]/10 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-20 -left-16 h-64 w-64 rounded-full bg-[var(--brand-secondary)]/10 blur-3xl"
        />

        <div className="relative grid items-center gap-8 lg:grid-cols-2">
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              <img
                src="/brand/vistazo-logo.png"
                alt="Vistazo — Aprende de un vistazo"
                className="h-14 w-auto object-contain"
              />
              <span className="vzt-float inline-flex items-center gap-1.5 rounded-full border border-[var(--border-subtle)] bg-white/90 px-3 py-1 text-xs font-bold text-[var(--brand-primary)] shadow-xs">
                <Sparkles className="h-3.5 w-3.5 text-[var(--brand-secondary)]" /> Microlearning Visual + IA
              </span>
            </div>

            <h1 className="text-3xl font-extrabold leading-tight sm:text-4xl">
              Domina habilidades reales en{' '}
              <span className="text-[var(--brand-primary)]">lecciones de 5 minutos</span>, incluso sin Wi-Fi.
            </h1>

            <p className="text-base text-[var(--text-secondary)]">
              LMS visual gamificado para brigadas de rescate, colegios, universidades y estudio libre: 7 tipos de retos
              interactivos con lectura por voz, repaso inteligente SM-2, estudio IA para docentes y certificados QR.
            </p>

            <div className="flex flex-wrap gap-3 pt-1">
              <Link
                to={user ? '/dashboard' : '/catalog'}
                className="btn-primary inline-flex items-center gap-2 px-6 py-3 text-sm font-bold"
              >
                <Compass className="h-4 w-4" />
                {user ? 'Ir a Mi Aprendizaje' : 'Explorar Catálogo Gratis'}
                <ArrowRight className="h-4 w-4" />
              </Link>
              {!user ? (
                <Link
                  to="/register"
                  className="inline-flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-white px-5 py-3 text-sm font-semibold transition hover:-translate-y-0.5 hover:bg-slate-50"
                >
                  Crear cuenta gratuita
                </Link>
              ) : (
                <Link
                  to="/unirse"
                  className="inline-flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-white px-5 py-3 text-sm font-semibold transition hover:-translate-y-0.5 hover:bg-slate-50"
                >
                  <School className="h-4 w-4 text-[var(--brand-primary)]" /> Entrar con código
                </Link>
              )}
            </div>

            <div className="flex flex-wrap gap-2 pt-2 text-[11px] font-semibold text-[var(--text-secondary)]">
              <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2.5 py-1 border border-[var(--border-subtle)]">
                <Radio className="h-3 w-3 text-indigo-600" /> Clases en Vivo
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2.5 py-1 border border-[var(--border-subtle)]">
                <HeartHandshake className="h-3 w-3 text-emerald-600" /> Portal Familiar
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2.5 py-1 border border-[var(--border-subtle)]">
                <WifiOff className="h-3 w-3 text-amber-600" /> Modo Offline PWA
              </span>
            </div>
          </div>

          {/* Vista previa interactiva de 30 segundos sin registro */}
          <div className="surface-card relative bg-white p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between gap-2">
              <span className="rounded-full bg-[var(--bg-accent-soft)] px-3 py-1 text-xs font-bold text-[var(--brand-primary)]">
                Pruébalo aquí en 30 s
              </span>
              <div className="flex items-center gap-2">
                <CelebrationBurst active={demoSubmitted && isDemoCorrect} badgeText="+15 XP" />
                <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-[11px] font-bold text-amber-900">
                  Rescate
                </span>
              </div>
            </div>
            <p className="font-bold text-base leading-snug">
              Llegas primero a un accidente vehicular. ¿Cuál es la acción prioritaria antes de intervenir?
            </p>
            <div className="space-y-2.5">
              {DEMO_OPTIONS.map((opt, idx) => {
                const selected = demoAnswer === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => {
                      setDemoAnswer(opt.id);
                      setDemoSubmitted(false);
                    }}
                    className={`group flex w-full items-center gap-3 rounded-xl border p-3.5 text-left text-xs font-semibold transition-all duration-150 ${
                      selected
                        ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)] ring-2 ring-[var(--brand-primary)]/20'
                        : 'border-[var(--border-subtle)] bg-white hover:border-[var(--brand-primary)]/50 hover:bg-slate-50'
                    }`}
                  >
                    <span
                      className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-[11px] font-extrabold transition ${
                        selected
                          ? 'bg-[var(--brand-primary)] text-white'
                          : 'bg-slate-100 text-[var(--text-secondary)] group-hover:bg-[var(--bg-accent-soft)]'
                      }`}
                    >
                      {String.fromCharCode(65 + idx)}
                    </span>
                    <span>{opt.text}</span>
                  </button>
                );
              })}
            </div>
            <button
              type="button"
              disabled={!demoAnswer}
              onClick={() => setDemoSubmitted(true)}
              className="btn-primary w-full py-2.5 text-xs font-bold disabled:opacity-50"
            >
              Comprobar respuesta al instante
            </button>
            {demoSubmitted && (
              <div
                className={`rounded-xl border p-3.5 text-xs ${
                  isDemoCorrect
                    ? 'vzt-pop border-emerald-300 bg-emerald-50 text-emerald-950'
                    : 'vzt-shake border-red-300 bg-red-50 text-red-950'
                }`}
              >
                <p className="flex items-center gap-1.5 font-bold">
                  {isDemoCorrect ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" /> ¡Excelente criterio! +15 XP de muestra
                    </>
                  ) : (
                    <>
                      <XCircle className="h-4 w-4 text-red-600" /> Riesgo crítico detectado
                    </>
                  )}
                </p>
                <p className="mt-1 leading-relaxed">
                  Siempre asegura la escena y colócate tu EPP antes de atender; evitar una segunda víctima protege todo
                  el operativo.
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Guía visual clara de 3 pasos para cualquier usuario nuevo */}
      <QuickGuideBanner
        title="¿Cómo funciona Vistazo en 3 pasos?"
        steps={[
          { num: '1', text: 'Elige tu rol al registrarte: Estudiante (aprende y compite) o Educador (crea cursos y aulas).' },
          { num: '2', text: 'Completa retos cortos visuales, con voz o dictado, en vivo o incluso sin internet.' },
          { num: '3', text: 'Repasa con tarjetas SM-2 / Anki y reclama tus certificados verificables con código QR.' },
        ]}
      />

      {/* Caminos rápidos claros: Estudiante vs Educador */}
      <section className="grid gap-4 md:grid-cols-2">
        <div className="surface-card interactive-card flex flex-col justify-between p-6 space-y-4">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
              <GraduationCap className="h-3.5 w-3.5" /> Para Estudiantes y Familias
            </span>
            <h2 className="text-xl font-bold">Aprende con retos visuales, audio y apuntes Anki</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Únete a un aula con su código `VZT-...`, estudia cursos libres gratuitos o consulta tu avance desde el Portal Familiar.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link to="/catalog" className="btn-primary inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold">
              Ver Catálogo Libre <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <Link
              to="/unirse"
              className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--border-subtle)] bg-white px-4 py-2 text-xs font-semibold hover:bg-slate-50"
            >
              Tengo un código de aula
            </Link>
            <Link
              to="/familia"
              className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--border-subtle)] bg-white px-4 py-2 text-xs font-semibold hover:bg-slate-50"
            >
              Portal Familiar
            </Link>
          </div>
        </div>

        <div className="surface-card interactive-card flex flex-col justify-between p-6 space-y-4">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--bg-accent-soft)] px-3 py-1 text-xs font-bold text-[var(--brand-primary)]">
              <Wand2 className="h-3.5 w-3.5" /> Para Educadores e Instituciones
            </span>
            <h2 className="text-xl font-bold">Crea cursos en minutos manualmente o con IA</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Sube tus PDF/DOCX, genera temarios, exámenes aleatorios, banco de preguntas, clases en vivo y certificados QR.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              to={user ? '/studio' : '/register'}
              className="btn-primary inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold"
            >
              {user ? 'Abrir Estudio Docente' : 'Crear cuenta de Educador'} <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <Link
              to="/planes"
              className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--border-subtle)] bg-white px-4 py-2 text-xs font-semibold hover:bg-slate-50"
            >
              Ver Planes SaaS
            </Link>
          </div>
        </div>
      </section>

      {/* Pilares PWA / Offline / SM-2 / Certificados */}
      <section className="grid gap-4 sm:grid-cols-3">
        <div className="surface-card interactive-card p-5 space-y-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--bg-accent-soft)] text-[var(--brand-primary)]">
            <WifiOff className="h-5 w-5" />
          </div>
          <h2 className="font-bold text-base">No pierdas tu racha sin Wi-Fi</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            PWA ligera instalable con sincronización automática al recuperar conexión en campo o transporte.
          </p>
        </div>
        <div className="surface-card interactive-card p-5 space-y-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--bg-accent-soft)] text-[var(--brand-primary)]">
            <Brain className="h-5 w-5" />
          </div>
          <h2 className="font-bold text-base">Memoria a largo plazo (SM-2)</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            Repaso espaciado automático, flashcards CSV Anki y tutor socrático IA tras 2 fallos.
          </p>
        </div>
        <div className="surface-card interactive-card p-5 space-y-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--bg-accent-soft)] text-[var(--brand-primary)]">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <h2 className="font-bold text-base">Certificados verificables por QR</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            Emisión automática en PDF al completar unidades obligatorias con hash criptográfico verificable.
          </p>
        </div>
      </section>

      {/* Selector interactivo de los 3 perfiles visuales */}
      <section className="surface-card p-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-bold">
              <Layers className="h-5 w-5 text-[var(--brand-primary)]" /> Adaptado a cada etapa educativa
            </h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Haz clic para ver cómo cambia en tiempo real todo el tema visual sin perder accesibilidad.
            </p>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full bg-[var(--bg-accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--brand-primary)]">
            <Smartphone className="h-4 w-4" /> Mobile-First
          </span>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          {profileSamples.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setUiProfile(p.id)}
              className={`interactive-card rounded-xl border p-4 text-left transition ${
                uiProfile === p.id
                  ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)] ring-2 ring-[var(--brand-primary)]/25'
                  : 'border-[var(--border-subtle)] bg-white hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="font-bold text-sm">{p.title}</p>
                <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-bold text-[var(--brand-primary)]">
                  {p.badge}
                </span>
              </div>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">{p.subtitle}</p>
            </button>
          ))}
        </div>
      </section>

      {/* Verificador rápido público de certificados */}
      <section className="surface-card p-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 font-bold text-base">
            <Award className="h-5 w-5 text-[var(--brand-secondary)]" /> Verificar un certificado institucional
          </h2>
          <p className="text-xs text-[var(--text-secondary)]">
            Consulta pública protegida contra enumeración sin exponer datos privados del estudiante.
          </p>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (verifyHash.trim()) navigate(`/verificar-certificado/${verifyHash.trim()}`);
          }}
          className="flex w-full max-w-md gap-2"
        >
          <input
            type="text"
            placeholder="Pega el hash SHA-256 del certificado..."
            value={verifyHash}
            onChange={(e) => setVerifyHash(e.target.value)}
            className="flex-1 rounded-xl border border-[var(--border-subtle)] bg-white px-3 py-2 text-xs"
          />
          <button type="submit" className="btn-primary px-4 py-2 text-xs font-semibold">
            Verificar
          </button>
        </form>
      </section>
    </div>
  );
}
