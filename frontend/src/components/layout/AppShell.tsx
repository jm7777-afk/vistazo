import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Award, BookOpen, Brain, Compass, Layers, LayoutDashboard, LogOut, Shield, UserCircle2, Users } from 'lucide-react';
import { useAppState } from '../../stores/AppContext';

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, activeOrg, setActiveOrgId, uiProfile, logout } = useAppState();
  const location = useLocation();

  const navItems = [
    { to: '/catalog', label: 'Catálogo Libre', icon: Compass, show: true },
    { to: '/dashboard', label: 'Mi Aprendizaje', icon: LayoutDashboard, show: Boolean(user) },
    { to: '/reviews', label: 'Repaso', icon: Brain, show: Boolean(user) },
    { to: '/library', label: 'Biblioteca', icon: Layers, show: Boolean(user) },
    { to: '/certificates', label: 'Certificados', icon: Award, show: Boolean(user) },
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
      <header className="sticky top-0 z-20 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <Link to="/catalog" className="flex items-center gap-2 font-bold tracking-tight text-[var(--brand-primary)]">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--brand-primary)] text-white text-sm">
              V
            </span>
            <span>Vistazo LMS</span>
            <span className="hidden rounded-full bg-[var(--bg-accent-soft)] px-2 py-0.5 text-xs font-medium text-[var(--brand-primary)] sm:inline">
              Perfil: {uiProfile}
            </span>
          </Link>

          <nav className="hidden items-center gap-1 md:flex" aria-label="Navegación principal">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = location.pathname.startsWith(item.to);
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition ${
                    active
                      ? 'bg-[var(--bg-accent-soft)] text-[var(--brand-primary)]'
                      : 'text-[var(--text-secondary)] hover:bg-slate-100'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
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
                className="max-w-[160px] rounded-lg border border-[var(--border-subtle)] bg-white px-2.5 py-1.5 text-xs font-medium"
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
                className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs font-semibold text-[var(--text-secondary)] hover:bg-slate-100"
              >
                <LogOut className="h-3.5 w-3.5" />
                Salir
              </button>
            ) : (
              <Link to="/login" className="btn-primary inline-flex items-center px-4 py-2 text-sm font-semibold">
                Ingresar
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 pb-24 md:pb-8">{children}</main>

      <nav
        className="fixed bottom-0 left-0 right-0 z-20 flex justify-around border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] py-2 md:hidden"
        aria-label="Navegación móvil"
      >
        {navItems.slice(0, 4).map((item) => {
          const Icon = item.icon;
          const active = location.pathname.startsWith(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex flex-col items-center gap-0.5 px-2 py-1 text-[11px] font-medium ${
                active ? 'text-[var(--brand-primary)]' : 'text-[var(--text-secondary)]'
              }`}
            >
              <Icon className="h-5 w-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
