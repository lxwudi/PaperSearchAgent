import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { apiFetch, login as apiLogin, refreshToken as apiRefresh, register as apiRegister, type TokenState } from '../api/client';
import type { Team, UserProfile } from '../api/types';

const STORAGE_ACCESS = 'ps_access';
const STORAGE_REFRESH = 'ps_refresh';
const STORAGE_USER = 'ps_user';
const STORAGE_TEAM = 'ps_team';

export type AuthContextValue = {
  user: UserProfile | null;
  tokens: TokenState | null;
  teams: Team[];
  activeTeamId: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<boolean>;
  selectTeam: (teamId: string) => void;
  createTeam: (name: string) => Promise<Team | null>;
  authFetch: <T>(path: string, options?: RequestInit) => Promise<T>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function storeTokens(tokens: TokenState | null) {
  if (!tokens) {
    localStorage.removeItem(STORAGE_ACCESS);
    localStorage.removeItem(STORAGE_REFRESH);
    return;
  }
  localStorage.setItem(STORAGE_ACCESS, tokens.accessToken);
  localStorage.setItem(STORAGE_REFRESH, tokens.refreshToken);
}

function storeUser(user: UserProfile | null) {
  if (!user) {
    localStorage.removeItem(STORAGE_USER);
    return;
  }
  localStorage.setItem(STORAGE_USER, JSON.stringify(user));
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [tokens, setTokens] = useState<TokenState | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [activeTeamId, setActiveTeamId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!tokens?.refreshToken) {
      return false;
    }
    const refreshed = await apiRefresh(tokens.refreshToken);
    if (!refreshed) {
      setTokens(null);
      storeTokens(null);
      return false;
    }
    setTokens(refreshed);
    storeTokens(refreshed);
    return true;
  }, [tokens?.refreshToken]);

  const authFetch = useCallback(
    async <T,>(path: string, options?: RequestInit) =>
      apiFetch<T>(path, {
        ...(options || {}),
        auth: tokens,
        refreshToken: async (refreshToken) => {
          const refreshed = await apiRefresh(refreshToken);
          if (refreshed) {
            setTokens(refreshed);
            storeTokens(refreshed);
          }
          return refreshed;
        },
      }),
    [tokens],
  );

  const loadTeams = useCallback(async () => {
    if (!tokens?.accessToken) {
      return;
    }
    const list = await authFetch<Team[]>('/teams');
    setTeams(list);
    if (list.length > 0 && !activeTeamId) {
      setActiveTeamId(list[0].id);
      localStorage.setItem(STORAGE_TEAM, list[0].id);
    }
  }, [authFetch, tokens?.accessToken, activeTeamId]);

  const loadMe = useCallback(async () => {
    if (!tokens?.accessToken) {
      return;
    }
    const profile = await authFetch<UserProfile>('/auth/me');
    setUser(profile);
    storeUser(profile);
  }, [authFetch, tokens?.accessToken]);

  const login = useCallback(async (email: string, password: string) => {
    const payload = await apiLogin(email, password);
    const nextTokens = { accessToken: payload.access_token, refreshToken: payload.refresh_token };
    setTokens(nextTokens);
    storeTokens(nextTokens);
    const profile: UserProfile = {
      id: payload.user_id,
      email: payload.email,
      display_name: payload.display_name,
      is_active: true,
    };
    setUser(profile);
    storeUser(profile);
    await loadTeams();
  }, [loadTeams]);

  const register = useCallback(async (email: string, password: string, displayName: string) => {
    const payload = await apiRegister(email, password, displayName);
    const nextTokens = { accessToken: payload.access_token, refreshToken: payload.refresh_token };
    setTokens(nextTokens);
    storeTokens(nextTokens);
    const profile: UserProfile = {
      id: payload.user_id,
      email: payload.email,
      display_name: payload.display_name,
      is_active: true,
    };
    setUser(profile);
    storeUser(profile);
    await loadTeams();
  }, [loadTeams]);

  const logout = useCallback(async () => {
    if (tokens?.refreshToken) {
      try {
        await apiFetch('/auth/logout', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: tokens.refreshToken }),
        });
      } catch {
        // ignore
      }
    }
    setTokens(null);
    setUser(null);
    setTeams([]);
    setActiveTeamId(null);
    storeTokens(null);
    storeUser(null);
    localStorage.removeItem(STORAGE_TEAM);
  }, [tokens]);

  const selectTeam = useCallback((teamId: string) => {
    setActiveTeamId(teamId);
    localStorage.setItem(STORAGE_TEAM, teamId);
  }, []);

  const createTeam = useCallback(async (name: string) => {
    if (!tokens?.accessToken) {
      return null;
    }
    const payload = await authFetch<Team>('/teams', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
    const nextTeams = [payload, ...teams];
    setTeams(nextTeams);
    selectTeam(payload.id);
    return payload;
  }, [authFetch, teams, tokens?.accessToken, selectTeam]);

  useEffect(() => {
    const storedAccess = localStorage.getItem(STORAGE_ACCESS);
    const storedRefresh = localStorage.getItem(STORAGE_REFRESH);
    const storedUser = localStorage.getItem(STORAGE_USER);
    const storedTeam = localStorage.getItem(STORAGE_TEAM);

    if (storedAccess && storedRefresh) {
      setTokens({ accessToken: storedAccess, refreshToken: storedRefresh });
    }
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        setUser(null);
      }
    }
    if (storedTeam) {
      setActiveTeamId(storedTeam);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!tokens?.accessToken) {
      return;
    }
    loadMe();
    loadTeams();
  }, [tokens?.accessToken, loadMe, loadTeams]);

  const value = useMemo(
    () => ({
      user,
      tokens,
      teams,
      activeTeamId,
      loading,
      login,
      register,
      logout,
      refresh,
      selectTeam,
      createTeam,
      authFetch,
    }),
    [user, tokens, teams, activeTeamId, loading, login, register, logout, refresh, selectTeam, createTeam, authFetch],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}


