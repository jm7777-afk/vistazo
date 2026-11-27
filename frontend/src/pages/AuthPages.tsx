import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { GraduationCap, Presentation } from 'lucide-react';
import { ErrorBanner, SuccessBanner } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { AccountType, TokenResponse, UIProfile, UserSummary } from '../types/api';

export function LoginPage() {
  const { loginSuccess } = useAppState();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = await apiRequest<TokenResponse>(
        '/auth/login',
        { method: 'POST', body: JSON.stringify({ email, password }) },
        false
      );
      loginSuccess(resp);
      navigate(resp.user.onboarding_completed === false ? '/onboarding' : '/dashboard');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md space-y-5">
      <div className="surface-card p-6">
        <img
          src="/brand/vistazo-logo.png"
          alt="Vistazo — Aprende de un vistazo"
          className="mx-auto mb-4 h-12 w-auto object-contain"
        />
        <h1 className="text-xl font-bold">Iniciar sesión</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Accede a tus aulas institucionales o continúa tu estudio libre.
        </p>

        {error && (
          <div className="mt-4">
            <ErrorBanner message={error} />
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <label className="block text-sm font-medium">
            Correo electrónico
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2.5 text-sm"
            />
          </label>
          <label className="block text-sm font-medium">
            Contraseña
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2.5 text-sm"
            />
          </label>
          <button type="submit" disabled={loading} className="btn-primary w-full py-2.5 text-sm font-semibold">
            {loading ? 'Verificando...' : 'Ingresar'}
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-[var(--text-secondary)]">
          ¿No tienes cuenta?{' '}
          <Link to="/register" className="font-semibold text-[var(--brand-primary)] underline">
            Regístrate aquí
          </Link>
        </p>
      </div>
    </div>
  );
}

export function RegisterPage() {
  const navigate = useNavigate();
  const [accountType, setAccountType] = useState<AccountType>('student');
  const [workspaceName, setWorkspaceName] = useState('');
  const [sectorType, setSectorType] = useState('specialized_training');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [uiProfile, setUiProfile] = useState<UIProfile>('pro');
  const [guardianName, setGuardianName] = useState('');
  const [guardianEmail, setGuardianEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const isMinorEstimate =
    accountType === 'student' &&
    Boolean(birthDate && new Date().getFullYear() - new Date(birthDate).getFullYear() < 14);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await apiRequest<UserSummary>(
        '/auth/register',
        {
          method: 'POST',
          body: JSON.stringify({
            email,
            password,
            full_name: fullName,
            account_type: accountType,
            workspace_name: accountType === 'educator' && workspaceName.trim() ? workspaceName.trim() : null,
            sector_type: sectorType,
            birth_date: birthDate || null,
            preferred_ui_profile: uiProfile,
            guardian_name: isMinorEstimate ? guardianName : null,
            guardian_email: isMinorEstimate ? guardianEmail : null,
          }),
        },
        false
      );
      setSuccess(
        accountType === 'educator'
          ? 'Cuenta docente y espacio de autoría creados correctamente. Ya puedes iniciar sesión.'
          : 'Cuenta creada correctamente. Ya puedes iniciar sesión.'
      );
      setTimeout(() => navigate('/login'), 1200);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg">
      <div className="surface-card p-6">
        <img
          src="/brand/vistazo-logo.png"
          alt="Vistazo — Aprende de un vistazo"
          className="mx-auto mb-4 h-12 w-auto object-contain"
        />
        <h1 className="text-xl font-bold">Crear cuenta</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Elige tu perfil inicial para preparar tu experiencia en Vistazo.
        </p>

        {error && (
          <div className="mt-4">
            <ErrorBanner message={error} />
          </div>
        )}
        {success && (
          <div className="mt-4">
            <SuccessBanner message={success} />
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="space-y-2">
            <span className="block text-sm font-bold text-[var(--text-primary)]">
              ¿Eres educador o estudiante?
            </span>
            <div className="grid gap-2.5 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => setAccountType('student')}
                className={`rounded-xl border p-3.5 text-left transition ${
                  accountType === 'student'
                    ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)] ring-2 ring-[var(--brand-primary)]/20'
                    : 'border-[var(--border-subtle)] bg-white hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center gap-2 font-bold text-sm text-[var(--brand-primary)]">
                  <GraduationCap className="h-4 w-4" /> Soy Estudiante
                </div>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  Aprende con micro-retos, repaso espaciado y certificados verificables.
                </p>
              </button>
              <button
                type="button"
                onClick={() => setAccountType('educator')}
                className={`rounded-xl border p-3.5 text-left transition ${
                  accountType === 'educator'
                    ? 'border-[var(--brand-primary)] bg-[var(--bg-accent-soft)] ring-2 ring-[var(--brand-primary)]/20'
                    : 'border-[var(--border-subtle)] bg-white hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center gap-2 font-bold text-sm text-[var(--brand-primary)]">
                  <Presentation className="h-4 w-4" /> Soy Educador
                </div>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  Carga materias, nodos, temarios, guías, pruebas fuertes e imágenes dinámicas con IA o manual.
                </p>
              </button>
            </div>
          </div>

          {accountType === 'educator' && (
            <div className="space-y-3 rounded-xl border border-[var(--brand-primary)]/30 bg-[var(--bg-accent-soft)]/50 p-3.5">
              <p className="text-xs font-bold text-[var(--brand-primary)]">
                Configuración de tu Espacio Docente (CRUD + Asistente IA)
              </p>
              <label className="block text-xs font-medium">
                Nombre de tu academia, cátedra o espacio (opcional)
                <input
                  type="text"
                  placeholder="Ej. Academia de Ciencias / Cátedra Prof. Vega"
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
                />
              </label>
              <label className="block text-xs font-medium">
                Área o nivel educativo principal
                <select
                  value={sectorType}
                  onChange={(e) => setSectorType(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
                >
                  <option value="specialized_training">Formación Especializada</option>
                  <option value="university">Universidad</option>
                  <option value="high_school">Bachillerato</option>
                  <option value="secondary_school">Educación Secundaria</option>
                  <option value="primary_school">Educación Primaria</option>
                  <option value="technical_academy">Academia Técnica</option>
                  <option value="rescue_brigade">Brigada de Rescate</option>
                </select>
              </label>
            </div>
          )}
          <label className="block text-sm font-medium">
            Nombre completo
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-sm font-medium">
            Correo electrónico
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-sm font-medium">
            Contraseña (mínimo 8 caracteres)
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm font-medium">
              Fecha de nacimiento
              <input
                type="date"
                value={birthDate}
                onChange={(e) => setBirthDate(e.target.value)}
                className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-sm font-medium">
              Perfil visual
              <select
                value={uiProfile}
                onChange={(e) => setUiProfile(e.target.value as UIProfile)}
                className="mt-1 w-full rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-2 text-sm"
              >
                <option value="pro">Profesional / Rescate</option>
                <option value="youth">Juvenil / Secundaria</option>
                <option value="kids">Infantil / Primaria</option>
              </select>
            </label>
          </div>

          {isMinorEstimate && (
            <div className="space-y-3 rounded-xl border border-amber-300 bg-amber-50 p-3.5">
              <p className="text-xs font-semibold text-amber-900">
                Consentimiento requerido para menores de edad
              </p>
              <label className="block text-xs font-medium">
                Nombre del representante legal
                <input
                  type="text"
                  required
                  value={guardianName}
                  onChange={(e) => setGuardianName(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm"
                />
              </label>
              <label className="block text-xs font-medium">
                Correo del representante legal
                <input
                  type="email"
                  required
                  value={guardianEmail}
                  onChange={(e) => setGuardianEmail(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm"
                />
              </label>
            </div>
          )}

          <button type="submit" disabled={loading} className="btn-primary w-full py-2.5 text-sm font-semibold">
            {loading ? 'Creando cuenta...' : 'Registrarme'}
          </button>
        </form>
      </div>
    </div>
  );
}
