const rawConfiguredBase = (import.meta.env.VITE_API_BASE_URL || '').trim();

// Local development deliberately talks to FastAPI directly. This keeps the
// terminal workflow independent from Netlify/Vite proxy configuration.
const isLocalBrowser = typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' ||
   window.location.hostname === '127.0.0.1' ||
   window.location.port === '5173');

const localBackendOrigin = typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : 'http://127.0.0.1:8000';

export const API_BASE = isLocalBrowser
  ? localBackendOrigin.replace(/\/+$/, '')
  : rawConfiguredBase.replace(/\/+$/, '');

export function apiUrl(path) {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE}${cleanPath}`;
}

export async function apiFetch(path, options = {}) {
  const controller = new AbortController();
  const timeoutMs = Number(options.timeoutMs || 45000);
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const requestOptions = { ...options, signal: options.signal || controller.signal };
    delete requestOptions.timeoutMs;
    return await fetch(apiUrl(path), requestOptions);
  } catch (error) {
    const message = error?.name === 'AbortError'
      ? `Request timed out after ${timeoutMs / 1000}s. Is the FastAPI backend running on port 8000?`
      : (error instanceof Error ? error.message : String(error));
    throw new Error(`Cannot reach the resume parsing backend. ${message}`);
  } finally {
    clearTimeout(timeoutId);
  }
}

export const hasRemoteBackend = Boolean(API_BASE);
