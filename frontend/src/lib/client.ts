import { getToken } from './api'

const base = () => import.meta.env.VITE_API_URL || ''

export async function apiCall(path: string, method = 'GET', body: any = null) {
  const r = await fetch(`${base()}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
    body: body ? JSON.stringify(body) : null
  })
  if (!r.ok) {
    let detail = ''
    try { detail = (await r.json()).detail || '' } catch { /* texte brut */ }
    throw new Error(detail ? `${path} : ${detail}` : `Erreur ${r.status} sur ${path}`)
  }
  return r.json()
}
