import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { CheckCircle2, School } from 'lucide-react';
import { ErrorBanner, LoadingState, SuccessBanner } from '../components/ui/StatusStates';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { InvitePreviewOut, JoinClassroomResponse, UserSummary } from '../types/api';

export function JoinClassroomPage() {
  const { inviteCode: paramCode } = useParams<{ inviteCode?: string }>();
  const navigate = useNavigate();
  const { user, updateUser, setActiveOrgId } = useAppState();
  const [codeInput, setCodeInput] = useState(paramCode ?? '');
  const [activeCode, setActiveCode] = useState(paramCode ?? '');

  const previewQuery = useQuery({
    queryKey: ['invite-preview', activeCode],
    queryFn: () => apiRequest<InvitePreviewOut>(`/classrooms/invite/${activeCode.trim().toUpperCase()}`, {}, false),
    enabled: activeCode.trim().length >= 4,
    retry: false,
  });

  const joinMutation = useMutation({
    mutationFn: () =>
      apiRequest<JoinClassroomResponse>('/classrooms/join', {
        method: 'POST',
        body: JSON.stringify({ invite_code: activeCode.trim().toUpperCase() }),
      }),
    onSuccess: async (res) => {
      try {
        const freshUser = await apiRequest<UserSummary>('/auth/me');
        updateUser(freshUser);
        setActiveOrgId(res.organization_id);
      } finally {
        setTimeout(() => navigate('/dashboard'), 1000);
      }
    },
  });

  const handleLookup = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveCode(codeInput.trim().toUpperCase());
  };

  return (
    <div className="mx-auto max-w-md space-y-5">
      <div className="surface-card p-6 space-y-4">
        <div className="flex items-center gap-2 text-[var(--brand-primary)] font-bold">
          <School className="h-5 w-5" /> Unirse a un Aula con Código
        </div>
        <p className="text-xs text-[var(--text-secondary)]">
          Ingresa el código compartido por tu docente o coordinador (ej. VZT-ABC123).
        </p>

        <form data-tour="join-code-box" onSubmit={handleLookup} className="flex gap-2">
          <input
            required
            placeholder="VZT-XXXXXX"
            value={codeInput}
            onChange={(e) => setCodeInput(e.target.value.toUpperCase())}
            className="flex-1 rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-sm font-mono uppercase"
          />
          <button type="submit" className="btn-primary px-4 py-2 text-xs font-semibold">
            Buscar
          </button>
        </form>

        {previewQuery.isLoading && <LoadingState label="Buscando aula..." />}
        {previewQuery.error && <ErrorBanner message={(previewQuery.error as Error).message} />}
        {joinMutation.error && <ErrorBanner message={(joinMutation.error as Error).message} />}
        {joinMutation.isSuccess && (
          <SuccessBanner message="¡Matriculado correctamente! Redirigiendo a tu panel..." />
        )}

        {previewQuery.data && (
          <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-accent-soft)] p-4 space-y-3">
            <div>
              <p className="text-xs font-bold uppercase text-[var(--brand-primary)]">
                {previewQuery.data.organization_name}
              </p>
              <h2 className="text-base font-bold">{previewQuery.data.classroom_name}</h2>
              <p className="text-xs text-[var(--text-secondary)]">
                Cohorte: {previewQuery.data.classroom_code} • Código: {previewQuery.data.invite_code}
              </p>
            </div>

            {user ? (
              <button
                type="button"
                disabled={!previewQuery.data.invite_enabled || joinMutation.isPending}
                onClick={() => joinMutation.mutate()}
                className="btn-primary w-full inline-flex items-center justify-center gap-1.5 py-2.5 text-xs font-bold disabled:opacity-50"
              >
                <CheckCircle2 className="h-4 w-4" />
                {joinMutation.isPending ? 'Matriculando...' : 'Unirme al Aula Ahora'}
              </button>
            ) : (
              <div className="space-y-2 text-xs">
                <p className="font-semibold">Inicia sesión o crea tu cuenta gratuita para matricularte:</p>
                <div className="flex gap-2">
                  <Link to="/login" className="btn-primary flex-1 py-2 text-center font-semibold">
                    Iniciar sesión
                  </Link>
                  <Link
                    to="/register"
                    className="flex-1 rounded-lg border border-[var(--border-subtle)] bg-white py-2 text-center font-semibold"
                  >
                    Registrarme
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
