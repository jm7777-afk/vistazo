import React, { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { KeyRound, ShieldCheck } from 'lucide-react';
import { ErrorBanner, SuccessBanner } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';

export function AccountRecoveryPage() {
  const [params] = useSearchParams();
  const resetToken = params.get('resetToken') ?? '';
  const verifyEmail = params.get('verifyEmail') ?? '';
  const verifyParent = params.get('verifyParent') ?? '';

  const [email, setEmail] = useState('');
  const [tokenInput, setTokenInput] = useState(resetToken);
  const [newPassword, setNewPassword] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleForgot = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await apiRequest<{ message: string }>('/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email }),
      }, false);
      setMessage(res.message);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await apiRequest<{ message: string }>('/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({ token: tokenInput, new_password: newPassword }),
      }, false);
      setMessage(res.message);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (endpoint: string, token: string) => {
    setError(null);
    setLoading(true);
    try {
      const res = await apiRequest<{ message: string }>(endpoint, {
        method: 'POST',
        body: JSON.stringify({ token }),
      }, false);
      setMessage(res.message);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md space-y-5">
      <div className="surface-card p-6 space-y-4">
        <h1 className="flex items-center gap-2 text-lg font-bold">
          <KeyRound className="h-5 w-5 text-[var(--brand-primary)]" /> Recuperación y Verificación de Cuenta
        </h1>

        {error && <ErrorBanner message={error} />}
        {message && <SuccessBanner message={message} />}

        {verifyEmail && (
          <div className="rounded-xl bg-slate-50 p-4 space-y-2">
            <p className="text-xs font-semibold">Confirmar verificación de correo electrónico:</p>
            <button
              type="button"
              disabled={loading}
              onClick={() => void handleVerify('/auth/verify-email', verifyEmail)}
              className="btn-primary w-full py-2 text-xs font-bold"
            >
              Verificar Mi Correo
            </button>
          </div>
        )}

        {verifyParent && (
          <div className="rounded-xl bg-amber-50 p-4 space-y-2">
            <p className="flex items-center gap-1.5 text-xs font-bold text-amber-950">
              <ShieldCheck className="h-4 w-4" /> Autorización Parental de Cuenta de Menor
            </p>
            <button
              type="button"
              disabled={loading}
              onClick={() => void handleVerify('/auth/verify-parental-consent', verifyParent)}
              className="btn-primary w-full py-2 text-xs font-bold"
            >
              Confirmar Autorización Parental
            </button>
          </div>
        )}

        {!resetToken && !verifyEmail && !verifyParent && (
          <form onSubmit={(e) => void handleForgot(e)} className="space-y-3">
            <p className="text-xs text-[var(--text-secondary)]">
              Ingresa tu correo para recibir instrucciones de recuperación de contraseña.
            </p>
            <input
              type="email"
              required
              placeholder="correo@ejemplo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
            />
            <button type="submit" disabled={loading} className="btn-primary w-full py-2 text-xs font-bold">
              Solicitar enlace de recuperación
            </button>
          </form>
        )}

        <form onSubmit={(e) => void handleReset(e)} className="space-y-3 border-t border-[var(--border-subtle)] pt-4">
          <p className="text-xs font-bold">¿Ya tienes un código / token de restablecimiento?</p>
          <input
            required
            placeholder="Token de recuperación"
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            className="w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-xs font-mono"
          />
          <input
            type="password"
            required
            minLength={8}
            placeholder="Nueva contraseña (mínimo 8 caracteres)"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm"
          />
          <button type="submit" disabled={loading} className="btn-primary w-full py-2 text-xs font-bold">
            Guardar Nueva Contraseña
          </button>
        </form>

        <p className="text-center text-xs">
          <Link to="/login" className="font-semibold text-[var(--brand-primary)] underline">
            Volver a Iniciar sesión
          </Link>
        </p>
      </div>
    </div>
  );
}
