import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Building2, CheckCircle2, CreditCard, Sparkles } from 'lucide-react';
import { apiRequest } from '../services/apiClient';
import { useAppState } from '../stores/AppContext';
import type { BillingPlanOut, SubscriptionOut } from '../types/api';

export function BillingPlansPage() {
  const { user } = useAppState();
  const queryClient = useQueryClient();
  const orgMemberships = user?.memberships ?? [];
  const [selectedOrgId, setSelectedOrgId] = useState(orgMemberships[0]?.organization_id ?? '');
  const [feedback, setFeedback] = useState<string | null>(null);

  const activeOrgId = selectedOrgId || orgMemberships[0]?.organization_id || '';

  const plansQuery = useQuery({
    queryKey: ['billing-plans'],
    queryFn: () => apiRequest<BillingPlanOut[]>('/billing/plans'),
  });

  const subQuery = useQuery({
    queryKey: ['org-subscription', activeOrgId],
    queryFn: () => apiRequest<SubscriptionOut>(`/orgs/${activeOrgId}/billing`),
    enabled: Boolean(activeOrgId),
  });

  const checkoutMutation = useMutation({
    mutationFn: (planCode: string) =>
      apiRequest<{ mode: string; subscription: SubscriptionOut }>(
        `/orgs/${activeOrgId}/billing/checkout`,
        {
          method: 'POST',
          body: JSON.stringify({ plan_code: planCode }),
        },
      ),
    onSuccess: (res) => {
      setFeedback(
        `Plan actualizado a ${res.subscription.plan_code.toUpperCase()} (${res.mode}). Cupo: ${res.subscription.max_students} estudiantes.`,
      );
      queryClient.invalidateQueries({ queryKey: ['org-subscription', activeOrgId] });
    },
  });

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="surface-card p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2 text-xl font-bold">
              <CreditCard className="h-5 w-5 text-[var(--brand-primary)]" /> Planes SaaS y Suscripción Institucional
            </h1>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Escala aulas, generaciones con IA y soporte de Stripe / webhooks por organización educativa.
            </p>
          </div>
          {orgMemberships.length > 0 && (
            <label className="flex items-center gap-2 text-xs font-semibold">
              <Building2 className="h-4 w-4 text-[var(--brand-primary)]" />
              <select
                value={activeOrgId}
                onChange={(e) => setSelectedOrgId(e.target.value)}
                className="rounded-lg border border-[var(--border-subtle)] bg-white px-3 py-1.5 text-sm"
              >
                {orgMemberships.map((m) => (
                  <option key={m.organization_id} value={m.organization_id}>
                    {m.organization_name} ({m.role_code})
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>

        {subQuery.data && (
          <div className="mt-4 flex flex-wrap items-center gap-4 rounded-xl bg-[var(--bg-accent-soft)] p-3.5 text-sm">
            <span>
              Plan actual:{' '}
              <strong className="uppercase text-[var(--brand-primary)]">
                {subQuery.data.plan_code}
              </strong>
            </span>
            <span>Estado: <strong>{subQuery.data.status}</strong></span>
            <span>Cupo estudiantes: <strong>{subQuery.data.max_students}</strong></span>
            <span>Generaciones IA / mes: <strong>{subQuery.data.monthly_ai_limit}</strong></span>
          </div>
        )}
        {feedback && (
          <p className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700">
            {feedback}
          </p>
        )}
      </div>

      <div data-tour="billing-plans" className="grid gap-4 md:grid-cols-3">
        {(plansQuery.data ?? []).map((plan) => {
          const isCurrent = subQuery.data?.plan_code === plan.plan_code;
          return (
            <div
              key={plan.plan_code}
              className={`surface-card flex flex-col justify-between p-6 ${
                plan.plan_code === 'educator_pro' ? 'border-2 border-[var(--brand-primary)]' : ''
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-bold">{plan.name}</h2>
                  {plan.plan_code === 'educator_pro' && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-[var(--bg-accent-soft)] px-2.5 py-0.5 text-[11px] font-bold text-[var(--brand-primary)]">
                      <Sparkles className="h-3 w-3" /> Recomendado
                    </span>
                  )}
                </div>
                <p className="mt-2 text-3xl font-extrabold">
                  ${plan.price_monthly_usd}
                  <span className="text-xs font-normal text-[var(--text-secondary)]"> / mes</span>
                </p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  Hasta {plan.max_students} estudiantes • {plan.monthly_ai_limit} usos IA/mes
                </p>
                <ul className="mt-4 space-y-2 text-xs text-[var(--text-secondary)]">
                  {plan.features.map((feat) => (
                    <li key={feat} className="flex items-start gap-1.5">
                      <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <button
                type="button"
                disabled={!activeOrgId || isCurrent || checkoutMutation.isPending}
                onClick={() => checkoutMutation.mutate(plan.plan_code)}
                className="btn-primary mt-6 w-full px-4 py-2.5 text-sm font-semibold disabled:opacity-50"
              >
                {!activeOrgId
                  ? 'Crea o únete a una institución'
                  : isCurrent
                    ? 'Plan activo'
                    : `Activar plan ${plan.name}`}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
