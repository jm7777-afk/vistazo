import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { Award, CheckCircle2, Download, ExternalLink, ShieldX } from 'lucide-react';
import { EmptyState, ErrorBanner, LoadingState } from '../components/ui/StatusStates';
import { API_BASE, apiRequest, getAccessToken } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { CertificateOut, PublicCertificateVerification } from '../types/api';

export function MyCertificatesPage() {
  const { user } = useAppState();
  const { data, isLoading, error } = useQuery({
    queryKey: ['my-certificates'],
    queryFn: () => apiRequest<CertificateOut[]>('/certificates/me'),
    enabled: Boolean(user),
  });

  if (!user) {
    return <EmptyState title="Certificados" description="Inicia sesión para consultar y descargar tus certificados." />;
  }
  if (isLoading) return <LoadingState label="Cargando certificados..." />;
  if (error) return <ErrorBanner message={(error as Error).message} />;

  const handleDownloadPdf = async (certId: string, certNumber: string) => {
    const token = getAccessToken();
    const res = await fetch(`${API_BASE}/certificates/${certId}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: 'include',
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${certNumber}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="surface-card p-6">
        <h1 className="flex items-center gap-2 text-xl font-bold">
          <Award className="h-5 w-5 text-[var(--brand-primary)]" /> Mis Certificados Verificables
        </h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Documentos oficiales con hash criptográfico único y código QR público.
        </p>
      </div>

      {!data || data.length === 0 ? (
        <EmptyState
          title="Aún no tienes certificados emitidos"
          description="Completa un pensum aprobado por tu institución para recibir tu certificado."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {data.map((cert) => (
            <article key={cert.id} className="surface-card p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm">{cert.certificate_number}</span>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                    cert.status === 'issued'
                      ? 'bg-emerald-100 text-emerald-900'
                      : cert.status === 'revoked'
                        ? 'bg-red-100 text-red-900'
                        : 'bg-amber-100 text-amber-900'
                  }`}
                >
                  {cert.status}
                </span>
              </div>
              <p className="text-xs text-[var(--text-secondary)]">Calificación final: {cert.final_grade}%</p>
              <div className="flex flex-wrap gap-2 pt-2">
                {cert.has_pdf && (
                  <button
                    type="button"
                    onClick={() => void handleDownloadPdf(cert.id, cert.certificate_number)}
                    className="btn-primary inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold"
                  >
                    <Download className="h-3.5 w-3.5" /> Descargar PDF
                  </button>
                )}
                <Link
                  to={`/verificar-certificado/${cert.verification_hash}`}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs font-semibold"
                >
                  <ExternalLink className="h-3.5 w-3.5" /> Verificación pública
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

export function VerifyCertificatePage() {
  const { hash } = useParams<{ hash: string }>();
  const { data, isLoading, error } = useQuery({
    queryKey: ['verify-certificate', hash],
    queryFn: () => apiRequest<PublicCertificateVerification>(`/verificar-certificado/${hash}`, {}, false),
    enabled: Boolean(hash),
  });

  if (isLoading) return <LoadingState label="Verificando autenticidad criptográfica..." />;
  if (error) return <ErrorBanner message={(error as Error).message} />;
  if (!data) return null;

  return (
    <div className="mx-auto max-w-lg">
      <div className="surface-card p-6 space-y-4">
        <div
          className={`flex items-center gap-3 rounded-xl p-4 ${
            data.valid ? 'bg-emerald-50 text-emerald-950' : 'bg-red-50 text-red-950'
          }`}
        >
          {data.valid ? (
            <CheckCircle2 className="h-7 w-7 shrink-0 text-emerald-600" />
          ) : (
            <ShieldX className="h-7 w-7 shrink-0 text-red-600" />
          )}
          <div>
            <h1 className="font-bold text-base">
              {data.valid ? 'Certificado Auténtico y Vigente' : 'Certificado Revocado o Inválido'}
            </h1>
            <p className="text-xs">Número: {data.certificate_number}</p>
          </div>
        </div>

        <dl className="space-y-2 text-sm">
          <div className="flex justify-between gap-4 border-b border-slate-100 pb-2">
            <dt className="text-[var(--text-secondary)]">Organización emisora</dt>
            <dd className="font-semibold text-right">{data.organization_name}</dd>
          </div>
          <div className="flex justify-between gap-4 border-b border-slate-100 pb-2">
            <dt className="text-[var(--text-secondary)]">Programa</dt>
            <dd className="font-semibold text-right">{data.program_title}</dd>
          </div>
          <div className="flex justify-between gap-4 border-b border-slate-100 pb-2">
            <dt className="text-[var(--text-secondary)]">Pensum</dt>
            <dd className="font-semibold text-right">{data.curriculum_title}</dd>
          </div>
          <div className="flex justify-between gap-4 border-b border-slate-100 pb-2">
            <dt className="text-[var(--text-secondary)]">Titular (iniciales)</dt>
            <dd className="font-semibold text-right">{data.recipient_initials}</dd>
          </div>
          <div className="flex justify-between gap-4 border-b border-slate-100 pb-2">
            <dt className="text-[var(--text-secondary)]">Calificación</dt>
            <dd className="font-semibold text-right">{data.final_grade}%</dd>
          </div>
          <div className="flex justify-between gap-4 border-b border-slate-100 pb-2">
            <dt className="text-[var(--text-secondary)]">Firma autorizada</dt>
            <dd className="font-semibold text-right">
              {data.signer_name} ({data.signer_title})
            </dd>
          </div>
          {data.revocation_reason && (
            <div className="rounded-lg bg-red-50 p-3 text-xs text-red-900">
              <strong>Motivo de revocación:</strong> {data.revocation_reason}
            </div>
          )}
        </dl>
      </div>
    </div>
  );
}
