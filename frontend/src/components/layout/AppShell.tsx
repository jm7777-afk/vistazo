import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Award, BookOpen, Brain, Compass, CreditCard, HeartHandshake, Layers, LayoutDashboard, LogOut, Menu, Palette, Shield, UserCircle2, Users, Wand2, WifiOff, X } from 'lucide-react';
import { flushOfflineAttempts, listOfflineAttempts } from '../../pwa/offlineQueue';
import { apiRequest } from '../../services/apiClient';
import { useAppState } from '../../stores/AppContext';
import type { UIProfile } from '../../types/api';
import { QuickHelpFab } from '../ui/QuickHelpFab';

const PROFILE_CYCLE: UIProfile[] = ['pro', 'youth', 'kids'];
const PROFILE_LABEL: Record<UIProfile, string> = {
  pro: 'Profesional',
  youth: 'Juvenil',
  kids: 'Infantil',
};

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, activeOrg, setActiveOrgId, uiProfile, setUiProfile, logout } = useAppState();
  const location = useLocation();
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [pendingSyncCount, setPendingSyncCount] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const cycleProfile = () => {
    const idx = PROFILE_CYCLE.indexOf(uiProfile);
    setUiProfile(PROFILE_CYCLE[(idx + 1) % PROFILE_CYCLE.length]);
  };

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const syncNow = async () => {
      const queued = await listOfflineAttempts();
      setPendingSyncCount(queued.length);
      if (navigator.onLine && queued.length > 0 && user) {
        await flushOfflineAttempts((item) =>
          apiRequest(`/challenges/${item.challenge_id}/attempt`, {
            method: 'POST',
            body: JSON.stringify({
              client_attempt_id: item.client_attempt_id,
              classroom_id: item.classroom_id,
              submitted_answer: item.submitted_answer,
              response_time_ms: item.response_time_ms,
            }),
          })
        );
        const remaining = await listOfflineAttempts();
        setPendingSyncCount(remaining.length);
      }
    };
    void syncNow();
    const onOnline = () => {
      setIsOffline(false);
      void syncNow();
    };
    const onOffline = () => setIsOffline(true);
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    return () => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }, [user]);

  const canAuthor = Boolean(
    user?.is_super_admin ||
      user?.account_type === 'educator' ||
      (activeOrg && ['instructor', 'coordinator'].includes(activeOrg.role_code))
  );

  const navItems = [
    { to: '/catalog', label: 'Catálogo Libre', icon: Compass, show: true },
    { to: '/dashboard', label: 'Mi Aprendizaje', icon: LayoutDashboard, show: Boolean(user) },
    { to: '/reviews', label: 'Repaso', icon: Brain, show: Boolean(user) },
    { to: '/library', label: 'Biblioteca', icon: Layers, show: Boolean(user) },
    { to: '/certificates', label: 'Certificados', icon: Award, show: Boolean(user) },
    { to: '/familia', label: 'Familia', icon: HeartHandshake, show: true },
    { to: '/planes', label: 'Planes', icon: CreditCard, show: canAuthor || Boolean(user?.is_super_admin) },
    { to: '/studio', label: 'Estudio', icon: Wand2, show: canAuthor },
    {
      to: '/instructor',
      label: 'Instructor',
      icon: BookOpen,
      show: Boolean(activeOrg && ['instructor', 'coordinator'].includes(activeOrg.role_code)),
    },
    {
      to: '/coordinator',
      label: 'Coordinación',
      icon: Users,
      show: Boolean(activeOrg && activeOrg.role_code === 'coordinator'),
    },
    { to: '/admin', label: 'SuperAdmin', icon: Shield, show: Boolean(user?.is_super_admin) },
    { to: '/profile', label: 'Perfil', icon: UserCircle2, show: Boolean(user) },
  ].filter((item) => item.show);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-30 border-b border-[var(--border-subtle)]/80 bg-[var(--bg-surface)]/85 backdrop-blur-md shadow-xs">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-2 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <Link to="/" className="group flex items-center gap-2 font-bold tracking-tight text-[var(--brand-primary)]">
              <img
                src="/brand/vistazo-icon.png"
                alt="Vistazo"
                className="h-8 w-auto object-contain transition-transform duration-200 group-hover:scale-105 sm:hidden"
              />
              <img
                src="/brand/vistazo-logo.png"
                alt="Vistazo — Aprende de un vistazo"
                className="hidden h-9 w-auto object-contain transition-transform duration-200 group-hover:scale-[1.03] sm:block"
              />
            </Link>
            <button
              type="button"
              onClick={cycleProfile}
              title="Cambiar estilo visual (Profesional / Juvenil / Infantil)"
              className="hidden items-center gap-1 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-accent-soft)] px-2.5 py-1 text-[11px] font-semibold text-[var(--brand-primary)] transition hover:brightness-95 lg:inline-flex"
            >
              <Palette className="h-3 w-3" />
              {PROFILE_LABEL[uiProfile]}
            </button>
          </div>

          <nav className="hidden items-center gap-1 md:flex" aria-label="Navegación principal">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = location.pathname.startsWith(item.to);
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`flex items-center gap-1.5 rounded-xl px-2.5 py-1.5 text-xs lg:text-sm font-semibold transition-all duration-150 ${
                    active
                      ? 'bg-[var(--brand-primary)] text-white shadow-xs'
                      : 'text-[var(--text-secondary)] hover:bg-[var(--bg-accent-soft)]/70 hover:text-[var(--brand-primary)]'
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="whitespace-nowrap">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-2">
            {user && user.memberships.length > 0 && (
              <select
                aria-label="Seleccionar organización activa"
                value={activeOrg?.organization_id ?? ''}
                onChange={(e) => setActiveOrgId(e.target.value || null)}
                className="max-w-[145px] rounded-xl border border-[var(--border-subtle)] bg-white px-2.5 py-1.5 text-xs font-medium"
              >
                {user.memberships.map((m) => (
                  <option key={m.organization_id} value={m.organization_id}>
                    {m.organization_name} ({m.role_code})
                  </option>
                ))}
                <option value="">Estudio Libre</option>
              </select>
            )}

            {user ? (
              <button
                type="button"
                onClick={() => void logout()}
                className="inline-flex items-center gap-1 rounded-xl border border-[var(--border-subtle)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--text-secondary)] transition hover:bg-slate-100"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Salir</span>
              </button>
            ) : (
              <Link to="/login" className="btn-primary inline-flex items-center px-4 py-2 text-xs sm:text-sm font-semibold">
                Ingresar
              </Link>
            )}

            <button
              type="button"
              onClick={() => setMobileMenuOpen((v) => !v)}
              aria-label="Abrir menú completo"
              className="inline-flex items-center justify-center rounded-xl border border-[var(--border-subtle)] bg-white p-2 text-[var(--text-secondary)] md:hidden"
            >
              {mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="vzt-scale-in border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-3 md:hidden">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase text-[var(--text-secondary)]">Todas las secciones</span>
              <button
                type="button"
                onClick={cycleProfile}
                className="inline-flex items-center gap-1 rounded-full bg-[var(--bg-accent-soft)] px-2.5 py-1 text-[11px] font-bold text-[var(--brand-primary)]"
              >
                <Palette className="h-3 w-3" /> Estilo: {PROFILE_LABEL[uiProfile]}
              </button>
            </div>
            <div className="grid grid-cols-2 gap-1.5">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = location.pathname.startsWith(item.to);
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={`flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold ${
                      active
                        ? 'bg-[var(--brand-primary)] text-white'
                        : 'bg-slate-50 text-[var(--text-primary)]'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 pb-24 md:pb-10">
        {(isOffline || pendingSyncCount > 0) && (
          <div className="vzt-pop mb-4 flex items-center justify-between rounded-xl border border-amber-300 bg-amber-50 px-4 py-2.5 text-xs font-semibold text-amber-950 shadow-xs">
            <span className="flex items-center gap-2">
              <WifiOff className="h-4 w-4" />
              {isOffline ? 'Modo sin conexión activo.' : 'Conexión restablecida.'}
            </span>
            {pendingSyncCount > 0 && <span>{pendingSyncCount} intentos en cola para sincronizar</span>}
          </div>
        )}
        <div key={location.pathname} className="vzt-fade-up">
          {children}
        </div>
      </main>

      <nav
        className="fixed bottom-0 left-0 right-0 z-20 flex justify-around border-t border-[var(--border-subtle)] bg-[var(--bg-surface)]/95 backdrop-blur-md py-1.5 md:hidden"
        aria-label="Navegación móvil"
      >
        {navItems.slice(0, 5).map((item) => {
          const Icon = item.icon;
          const active = location.pathname.startsWith(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex flex-col items-center gap-0.5 rounded-lg px-2 py-1 text-[10px] font-semibold transition ${
                active ? 'text-[var(--brand-primary)] scale-105' : 'text-[var(--text-secondary)]'
              }`}
            >
              <Icon className="h-5 w-5" />
              <span className="truncate max-w-[64px]">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <QuickHelpFab />
    </div>
  );
}
