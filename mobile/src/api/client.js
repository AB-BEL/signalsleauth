const BASE = import.meta.env.VITE_API_BASE || ''

function token() {
  return localStorage.getItem('ss_token') || ''
}

export async function api(path, options = {}) {
  const headers = {
    Accept: 'application/json',
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(token() ? { Authorization: `Bearer ${token()}` } : {}),
    ...(options.headers || {}),
  }
  let res
  try {
    res = await fetch(BASE + path, {
      ...options,
      headers,
      body: options.body != null ? JSON.stringify(options.body) : undefined,
    })
  } catch (e) {
    throw new Error('Failed to fetch — is the API running and VITE_API_BASE correct?')
  }
  const text = await res.text()
  let data = {}
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`Invalid server response (${res.status})`)
  }
  if (!res.ok || data.ok === false) {
    throw new Error(data.error || data.message || `HTTP ${res.status}`)
  }
  return data
}

export const authApi = {
  login: (email, password) => api('/api/auth/login', { method: 'POST', body: { email, password } }),
  register: (payload) => api('/api/auth/register', { method: 'POST', body: payload }),
  me: () => api('/api/me'),
}

export const gameApi = {
  dashboard: () => api('/api/dashboard'),
  rankings: (chapter) => api(chapter ? `/api/rankings?chapter=${chapter}` : '/api/rankings'),
  playInfo: (chapter) => api(`/api/chapter/${chapter}/play-info`),
  gamePackage: (chapter) => api(`/api/chapter/${chapter}/game-package`),
  submitScore: (payload) => api('/api/submit-score', { method: 'POST', body: payload }),
  myScores: (chapter) => api(`/api/my-scores/${chapter}`),
}

/** Public API origin for iframe HTML games */
export function apiBase() {
  return BASE || (typeof window !== 'undefined' ? window.location.origin : '')
}
