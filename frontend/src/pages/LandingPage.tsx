import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Award, Brain, CheckCircle2, Compass, Layers, ShieldCheck, Smartphone, WifiOff, XCircle } from 'lucide-react';
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

  const profileSamples: { id: UIProfile; title: string; subtitle: string }[] = [
    { id: 'kids', title: 'Infantil y Primaria', subtitle: 'Botones amplios y tonos cálidos' },
    { id: 'youth', title: 'Juvenil y Secundaria', subtitle: 'Dinámico, visual y ágil' },
    { id: 'pro', title: 'Profesional y Rescate', subtitle: 'Sobrio, técnico y preciso' },
  ];

  const isDemoCorrect = demoAnswer === 'b';

  return (
    <div className="space-y-10">
      {/* Hero con propuesta de valor clara + vista previa interactiva en vivo */}
      <section className="surface-card overflow-hidden bg-gradient-to-br from-[var(--bg-surface)] to-[var(--bg-accent-soft)] p-6 sm:p-10">
        <div className="grid items-center gap-8 lg:grid-cols-2">
          <div className="space-y-5">
            <img
              src="/brand/vistazo-logo.png"
              alt="Vistazo — Aprende de un vistazo"
              className="h-14 w-auto object-contain"
            />
            <h1 className="text-3xl font-extrabold leading-tight sm:text-4xl">
              Domina habilidades reales en lecciones de 5 minutos, incluso sin Wi-Fi.
            </h1>
            <p className="text-base text-[var(--text-secondary)]">
              LMS visual gamificado para brigadas de rescate, universidades, colegios y estudio libre: 6 tipos de retos
              interactivos, repetición espaciada SM-2, tutor socrático IA y certificados verificables con QR.
            </p>
            <div className="flex flex-wrap gap-3 pt-1">
              <Link
                to={user ? '/dashboard' : '/catalog'}
                className="btn-primary inline-flex items-center gap-2 px-6 py-3 text-sm font-bold shadow-sm"
              >
                <Compass className="h-4 w-4" />
                {user ? 'Ir a Mi Aprendizaje' : 'Probar Catálogo Libre Gratis'}
              </Link>
              {!user && (
                <Link
                  to="/register"
                  className="inline-flex items-center gap-2 rounded-lg border border-[var(--border-subtle)] bg-white px-5 py-3 text-sm font-semibold hover:bg-slate-50"
                >
                  Crear cuenta gratuita
                </Link>
              )}
            </div>
          </div>

          {/* Vista previa interactiva de 30 segundos sin registro */}
          <div className="surface-card bg-white p-5 shadow-md space-y-3">
            <div className="flex items-center justify-between">
              <span className="rounded-full bg-[var(--bg-accent-soft)] px-3 py-1 text-xs font-bold text-[var(--brand-primary)]">
                Reto interactivo de muestra (30 s)
              </span>
              <span className="text-xs font-semibold text-amber-800">Protocolo Rescate</span>
            </div>
            <p className="font-bold text-sm">
              Llegas primero a un accidente vehicular. ¿Cuál es la acción prioritaria antes de intervenir?
            </p>
            <div className="space-y-2">
              {DEMO_OPTIONS.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => {
                    setDemoAnswer(opt.id);
                    setDemoSubmitted(false);
                  }}
                  className={`w-full rounded-xl border p-3 text-left text-xs font-medium transition ${
                    demoAnswer === opt.id
                      ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)]'
                      : 'border-[var(--border-subtle)] hover:bg-slate-50'
                  }`}
                >
                  {opt.text}
                </button>
              ))}
            </div>
            <button
              type="button"
              disabled={!demoAnswer}
              onClick={() => setDemoSubmitted(true)}
              className="btn-primary w-full py-2 text-xs font-bold disabled:opacity-50"
            >
              Comprobar respuesta al instante
            </button>
            {demoSubmitted && (
              <div
                className={`rounded-xl p-3 text-xs ${
                  isDemoCorrect ? 'bg-emerald-50 text-emerald-950' : 'bg-red-50 text-red-950'
                }`}
              >
                <p className="flex items-center gap-1.5 font-bold">
                  {isDemoCorrect ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" /> ¡Correcto! +15 XP
                    </>
                  ) : (
                    <>
                      <XCircle className="h-4 w-4 text-red-600" /> Riesgo crítico detectado
                    </>
                  )}
                </p>
                <p className="mt-1">
                  Siempre asegura la escena y colócate tu EPP antes de atender; evitar una segunda víctima protege todo
                  el operativo.
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Pilares PWA / Offline / SM-2 / Certificados */}
      <section className="grid gap-4 sm:grid-cols-3">
        <div className="surface-card p-5 space-y-2">
          <WifiOff className="h-6 w-6 text-[var(--brand-primary)]" />
          <h2 className="font-bold text-base">No pierdas tu racha sin Wi-Fi</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            PWA ligera instalable con sincronización automática al recuperar conexión en campo o transporte.
          </p>
        </div>
        <div className="surface-card p-5 space-y-2">
          <Brain className="h-6 w-6 text-[var(--brand-primary)]" />
          <h2 className="font-bold text-base">Memoria a largo plazo (SM-2)</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            Repaso espaciado automático, biblioteca visual flash y tutor socrático IA tras 2 fallos.
          </p>
        </div>
        <div className="surface-card p-5 space-y-2">
          <ShieldCheck className="h-6 w-6 text-[var(--brand-primary)]" />
          <h2 className="font-bold text-base">Certificados verificables por QR</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            Pensums versionados por cohorte, emisión en PDF con firma criptográfica y validación pública instantánea.
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
              Prueba en vivo cómo cambia el sistema visual sin perder legibilidad ni accesibilidad.
            </p>
          </div>
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--brand-primary)]">
            <Smartphone className="h-4 w-4" /> Mobile-First
          </span>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          {profileSamples.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setUiProfile(p.id)}
              className={`rounded-xl border p-4 text-left transition ${
                uiProfile === p.id
                  ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)] ring-2 ring-[var(--brand-primary)]/20'
                  : 'border-[var(--border-subtle)] bg-white hover:bg-slate-50'
              }`}
            >
              <p className="font-bold text-sm">{p.title}</p>
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
            className="flex-1 rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-xs"
          />
          <button type="submit" className="btn-primary px-4 py-2 text-xs font-semibold">
            Verificar
          </button>
        </form>
      </section>
    </div>
  );
}
