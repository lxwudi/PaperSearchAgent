import type { AuthResponse } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const getApiBase = () => API_BASE;
export const getWsBase = () => API_BASE.replace(/^http/, 'ws');

export type TokenState = {
  accessToken: string;
  refreshToken: string;
};

export type TokenRefresher = (refreshToken: string) => Promise<TokenState | null>;

export type RequestOptions = RequestInit & {
  auth?: TokenState | null;
  refreshToken?: TokenRefresher;
};

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');
  if (options.auth?.accessToken) {
    headers.set('Authorization', `Bearer ${options.auth.accessToken}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && options.auth?.refreshToken && options.refreshToken) {
    const refreshed = await options.refreshToken(options.auth.refreshToken);
    if (refreshed) {
      const retryHeaders = new Headers(options.headers || {});
      retryHeaders.set('Content-Type', 'application/json');
      retryHeaders.set('Authorization', `Bearer ${refreshed.accessToken}`);
      const retry = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: retryHeaders,
      });
      if (!retry.ok) {
        throw new Error(await retry.text());
      }
      return (await retry.json()) as T;
    }
  }

  if (!response.ok) {
    throw new Error(await response.text());
  }

  if (response.status === 204) {
    return {} as T;
  }

  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as AuthResponse;
}

export async function register(email: string, password: string, displayName: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, display_name: displayName }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as AuthResponse;
}

export async function refreshToken(refreshToken: string): Promise<TokenState | null> {
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) {
    return null;
  }
  const payload = (await response.json()) as AuthResponse;
  return { accessToken: payload.access_token, refreshToken: payload.refresh_token };
}
