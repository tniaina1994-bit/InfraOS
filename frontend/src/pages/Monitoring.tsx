import React from 'react'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Stat, Card, Msg, Spinner } from '../components/ui'

export default function Monitoring() {
  const [cur, setCur] = React.useState<any>(null)
  const [hist, setHist] = React.useState<any[]>([])
  const [agents, setAgents] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  async function load() {
    try {
      setCur(await apiGet('/api/v1/monitoring/current'))
      setHist((await apiGet<{ samples: any[] }>('/api/v1/monitoring/history?limit=20')).samples)
      setAgents((await apiGet<{ agents: any[] }>('/api/v1/monitoring/agents')).agents)
    } catch (e: any) { setMsg(e.message || String(e)) }
    finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])
  const bar = (v: number) => (
    <div className="h-2 rounded bg-slate-800 mt-1">
      <div className={`h-2 rounded ${v > 90 ? 'bg-red-500' : v > 70 ? 'bg-yellow-500' : 'bg-green-500'}`} style={{ width: `${Math.min(v, 100)}%` }} />
    </div>
  )
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Monitoring serveur</h2>
      <Msg text={msg} />
      {loading && <Spinner label="Chargement des métriques…" />}
      {!loading && (
      <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="CPU" value={`${cur?.cpu ?? '…'} %`} />
        <Stat label="RAM" value={`${cur?.mem ?? '…'} %`} />
        <Stat label="Disque" value={`${cur?.disk ?? '…'} %`} />
        <Stat label="Charge (1 min)" value={String(cur?.load1 ?? '…')} />
      </div>
      <Card title="Détails">
        <div className="text-sm space-y-1">
          <div>Processus : <b>{cur?.processes ?? '…'}</b> · Uptime : <b>{cur ? Math.round(cur.uptime / 3600) + ' h' : '…'}</b> · Température : <b>{cur?.temp || '—'}</b></div>
          <div>Réseau : RX <b>{cur ? Math.round(cur.net_rx / 1e6) + ' Mo' : '…'}</b> · TX <b>{cur ? Math.round(cur.net_tx / 1e6) + ' Mo' : '…'}</b></div>
          {bar(cur?.cpu || 0)}
        </div>
        <button className="btn mt-3" onClick={() => apiCall('/api/v1/monitoring/collect', 'POST').then(() => { setMsg('Échantillon enregistré'); load() }).catch((e: any) => setMsg(e.message))}>Enregistrer un échantillon</button>
      </Card>
      <Card title="Historique (20 derniers)">
        {hist.map((h: any, i: number) => (
          <div key={i} className="text-xs font-mono py-0.5">
            {String(h.ts).slice(11, 19)} · CPU {h.cpu}% · RAM {h.mem}% · charge {h.load1}
          </div>
        ))}
        {hist.length === 0 && <p className="text-sm text-slate-400">Aucun échantillon — cliquez ci-dessus.</p>}
      </Card>
      <Card title={`Agents (${agents.length})`}>
        {agents.map((a: any) => (
          <div key={a.hostname} className="text-sm py-1">{a.hostname} <span className="text-xs text-slate-400">({a.os}) — vu : {a.last_seen || 'jamais'}</span></div>
        ))}
        {agents.length === 0 && <p className="text-sm text-slate-400">Aucun agent — voir docs/AGENT.md pour en connecter (Linux/Windows).</p>}
      </Card>
      </>
      )}
    </div>
  )
}
