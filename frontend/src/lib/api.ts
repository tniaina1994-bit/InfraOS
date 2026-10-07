export function getToken(): string | null {
  return localStorage.getItem('infraos_token')
}

export async function apiLogin(username: string, password: string) {
  const base = import.meta.env.VITE_API_URL || ''
  const r = await fetch(`${base}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  })
  if (!r.ok) throw new Error(`Login ${r.status}`)
  const data = await r.json()
  localStorage.setItem('infraos_token', data.access_token)
  return data
}

export async function apiGet<T>(path: string): Promise<T> {
  const base = import.meta.env.VITE_API_URL || ''
  const headers: Record<string, string> = {}
  const t = getToken()
  if (t) headers['Authorization'] = `Bearer ${t}`
  const r = await fetch(`${base}${path}`, { headers })
  if (r.status === 401) { localStorage.removeItem('infraos_token'); window.location.href = '/login' }
  if (!r.ok) throw new Error(`API ${r.status} ${path}`)
  return r.json() as Promise<T>
}
