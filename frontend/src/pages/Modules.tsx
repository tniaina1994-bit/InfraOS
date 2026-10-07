import React from 'react'
import { apiGet, getToken } from '../lib/api'
import { Card, Badge, Msg, Spinner, Skeleton } from '../components/ui'

async function apiPost(path: string, body = {}) {
  const base = import.meta.env.VITE_API_URL || ''
  const r = await fetch(`${base}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
    body: JSON.stringify(body)
  })
  if (!r.ok) {
    let detail = ''
    try { detail = (await r.json()).detail || '' } catch { /* vide */ }
    throw new Error(detail || `Erreur ${r.status}`)
  }
  return r.json()
}

export default function Modules() {
  const [mods, setMods] = React.useState<any[]>([])
  const [order, setOrder] = React.useState<string[]>([])
  const [loading, setLoading] = React.useState(true)
  const [err, setErr] = React.useState('')
  async function load() {
    try {
      const d = await apiGet<{ modules: any[]; order: string[] }>('/api/v1/modules')
      setMods(d.modules)
      setOrder(d.order || [])
    } catch (e: any) { setErr(e.message || String(e)) }
    finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])
  async function toggle(m: any) {
    try { await apiPost(`/api/v1/modules/${m.name}/${m.enabled ? 'disable' : 'enable'}`); await load() }
    catch (e: any) { setErr(e.message || String(e)) }
  }
  async function uninstall(m: any) {
    if (!confirm(`Désinstaller ${m.display_name || m.name} (paquets Debian retirés) ?`)) return
    try { await apiPost(`/api/v1/modules/${m.name}/uninstall`); await load() }
    catch (e: any) { setErr(e.message || String(e)) }
  }
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Modules du monolithe</h2>
      {err && <div className="card text-red-300">{err}</div>}
      {loading && !err && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card"><Skeleton lines={3} /></div>
          ))}
        </div>
      )}
      {order.length > 0 && order[0].startsWith(' ordre') && (
        <div className="card text-yellow-300 text-sm">Ordre de démarrage partiel : dépendance manquante.</div>
      )}
      {!loading && (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {mods.map((m) => (
          <div key={m.name} className="card">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">{m.display_name || m.title || m.name}</h3>
              <Badge value={m.error ? 'erreur' : m.enabled ? 'activé' : 'désactivé'} good={['activé']} bad={['erreur']} />
            </div>
            <p className="text-xs text-slate-400 mt-1">{m.description || `${m.name} v${m.version}`}</p>
            <div className="text-xs mt-2 space-y-0.5">
              <div>Installé : <b>{m.installed == null ? '—' : m.installed ? 'oui' : 'non'}</b> · En cours : <b>{m.running == null ? '—' : m.running ? 'oui' : 'non'}</b> {m.managed ? '· géré' : '· manifeste seul'}</div>
              {m.detail && <div className="text-slate-300">{m.detail}</div>}
              {(m.dependencies?.length > 0) && <div className="text-slate-400">Dépendances : {m.dependencies.join(', ')}</div>}
              {(m.services?.length > 0) && <div className="text-slate-400">Services : {m.services.join(', ')}</div>}
            </div>
            {!m.error && (
              <div className="flex gap-2 mt-2">
                <button className="btn" onClick={() => toggle(m)}>{m.enabled ? 'Désactiver' : 'Activer'}</button>
                <button className="btn bg-red-700 hover:bg-red-600" onClick={() => uninstall(m)}>Désinstaller</button>
              </div>
            )}
          </div>
        ))}
      </div>
      )}
    </div>
  )
}
