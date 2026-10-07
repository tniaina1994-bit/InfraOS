import React from 'react'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Table, StatusDot, Msg, Spinner } from '../components/ui'

export default function VPN() {
  const [servers, setServers] = React.useState<any[]>([])
  const [peers, setPeers] = React.useState<Record<number, any[]>>({})
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  async function load() {
    try { setServers((await apiGet<{ servers: any[] }>('/api/v1/vpn/servers')).servers) }
    catch (e: any) { setMsg(e.message || String(e)) }
    finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])
  async function showPeers(s: any) {
    try { setPeers({ ...peers, [s.id]: (await apiGet<{ peers: any[] }>(`/api/v1/vpn/servers/${s.id}/peers`)).peers }) }
    catch (e: any) { setMsg(e.message || String(e)) }
  }
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">VPN (WireGuard)</h2>
      <Msg text={msg} />
      {loading && <Spinner label="Chargement du VPN…" />}
      {!loading && (
        <>
          <Card title="Serveurs" right={<button className="btn" onClick={() => apiCall('/api/v1/vpn/servers', 'POST', { name: 'wg0', address: '10.8.0.1/24', port: 51820 }).then(() => { setMsg('Serveur wg0 créé (clés générées)'); load() }).catch((e: any) => setMsg(e.message))}>Créer wg0</button>}>
            {servers.map((s) => (
              <div key={s.id} className="border-b border-slate-800/50 py-2">
                <div className="flex items-center gap-2 text-sm">
                  <StatusDot active={!!s.up} />
                  <b>{s.name}</b>
                  <span className="font-mono text-slate-300">{s.address}:{s.port}</span>
                  <span className="text-slate-400">{s.peers ?? 0} peer(s)</span>
                  <button className="btn" onClick={() => showPeers(s)}>Pairs</button>
                  <button className="btn" onClick={() => apiCall(`/api/v1/vpn/servers/${s.id}/apply`, 'POST').then(() => { setMsg(`${s.name} appliqué`); load() }).catch((e: any) => setMsg(e.message))}>Appliquer</button>
                </div>
                {(peers[s.id] || []).map((p: any) => (
                  <div key={p.id} className="text-xs text-slate-400 ml-6 py-0.5">
                    {p.name} — <span className="font-mono">{p.allowed_ips}</span> {p.endpoint && `via ${p.endpoint}`}
                  </div>
                ))}
              </div>
            ))}
            {servers.length === 0 && <p className="text-sm text-slate-400">Aucun serveur — créez wg0.</p>}
          </Card>
        </>
      )}
    </div>
  )
}
