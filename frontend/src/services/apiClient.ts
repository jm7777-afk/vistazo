function resolveApiBase(): string {
  const raw = (import.meta.env.VITE_API_URL ?? '').trim().replace(/\/+$/, '');
  if (!raw) return '/api/v1';
  return raw.endsWith('/api/v1') ? raw : `${raw}/api/v1`;
}

export const API_BASE = resolveApiBase();
export const API_ORIGIN = API_BASE.replace(/\/api\/v1$/, '');

let accessTokenMemory: string | null = null;
let csrfTokenMemory: string | null = null;

export function setSessionTokens(accessToken: string | null, csrfToken: string | null): void {
  accessTokenMemory = accessToken;
  csrfTokenMemory = csrfToken;
}

export function getAccessToken(): string | null {
  return accessTokenMemory;
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function tryRefresh(): Promise<boolean> {
  if (!csrfTokenMemory) return false;
  const res = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'X-CSRF-Token': csrfTokenMemory,
    },
  });
  if (!res.ok) {
    setSessionTokens(null, null);
    return false;
  }
  const data = await res.json();
  setSessionTokens(data.access_token, data.csrf_token);
  return true;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  retryOnAuth = true
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }
  if (accessTokenMemory) {
    headers.set('Authorization', `Bearer ${accessTokenMemory}`);
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      credentials: 'include',
      headers,
    });
  } catch {
    throw new ApiError(
      0,
      'network_error',
      `No se pudo conectar con la API (${API_BASE}). Verifica que el backend esté activo, CORS_ORIGINS coincida y VITE_API_URL sea correcta.`
    );
  }

  if (res.status === 401 && retryOnAuth && (await tryRefresh())) {
    return apiRequest<T>(path, options, false);
  }

  if (!res.ok) {
    let code = 'request_error';
    let message = `Error ${res.status}`;
    try {
      const payload = await res.json();
      if (payload?.error) {
        code = payload.error.code ?? code;
        message = payload.error.message ?? message;
      } else if (payload?.detail) {
        message = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail);
      }
    } catch {
      // Respuesta sin JSON
    }
    throw new ApiError(res.status, code, message);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}
