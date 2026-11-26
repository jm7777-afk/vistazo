import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ErrorBanner, SuccessBanner } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { TokenResponse, UIProfile, UserSummary } from '../types/api';

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
      navigate('/dashboard');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md space-y-5">
      <div className="surface-card p-6">
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

  const isMinorEstimate = Boolean(birthDate && new Date().getFullYear() - new Date(birthDate).getFullYear() < 14);

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
            birth_date: birthDate || null,
            preferred_ui_profile: uiProfile,
            guardian_name: isMinorEstimate ? guardianName : null,
            guardian_email: isMinorEstimate ? guardianEmail : null,
          }),
        },
        false
      );
      setSuccess('Cuenta creada correctamente. Ya puedes iniciar sesión.');
      setTimeout(() => navigate('/login'), 1200);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md">
      <div className="surface-card p-6">
        <h1 className="text-xl font-bold">Crear cuenta</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">Registro gratuito para estudio libre o instituciones.</p>

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

        <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
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
