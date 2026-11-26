import React, { createContext, useContext, useEffect, useState } from 'react';
import { apiRequest, setSessionTokens } from '../services/apiClient';
import type { MembershipSummary, TokenResponse, UIProfile, UserSummary } from '../types/api';

interface AppContextValue {
  user: UserSummary | null;
  activeOrg: MembershipSummary | null;
  uiProfile: UIProfile;
  setActiveOrgId: (orgId: string | null) => void;
  setUiProfile: (profile: UIProfile) => void;
  loginSuccess: (resp: TokenResponse) => void;
  logout: () => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserSummary | null>(null);
  const [activeOrgId, setActiveOrgId] = useState<string | null>(null);
  const [uiProfile, setUiProfile] = useState<UIProfile>('pro');

  const activeOrg = user?.memberships.find((m) => m.organization_id === activeOrgId) ?? null;

  useEffect(() => {
    document.documentElement.setAttribute('data-theme-profile', uiProfile);
  }, [uiProfile]);

  const loginSuccess = (resp: TokenResponse) => {
    setSessionTokens(resp.access_token, resp.csrf_token);
    setUser(resp.user);
    const firstOrg = resp.user.memberships[0] ?? null;
    setActiveOrgId(firstOrg ? firstOrg.organization_id : null);
    setUiProfile(firstOrg ? firstOrg.default_ui_profile : resp.user.preferred_ui_profile);
  };

  const logout = async () => {
    try {
      await apiRequest<void>('/auth/logout', { method: 'POST' }, false);
    } finally {
      setSessionTokens(null, null);
      setUser(null);
      setActiveOrgId(null);
      setUiProfile('pro');
    }
  };

  return (
    <AppContext.Provider
      value={{
        user,
        activeOrg,
        uiProfile,
        setActiveOrgId: (id) => {
          setActiveOrgId(id);
          const found = user?.memberships.find((m) => m.organization_id === id);
          if (found) setUiProfile(found.default_ui_profile);
        },
        setUiProfile,
        loginSuccess,
        logout,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppState(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppState debe usarse dentro de AppStateProvider');
  return ctx;
}
