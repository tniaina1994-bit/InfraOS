import React from 'react'
import { apiGet } from '../lib/api'
import { Stat, Card, Msg, Spinner, Skeleton } from '../components/ui'

export default function Security() {
  const [ov, setOv] = React.useState<any>(null)
  const [syslogs, setSyslogs] = React.useState('')
  const [fwlogs, setFwlogs] = React.useState('')
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  React.useEffect(() => {
    apiGet('/api/v1/security/overview').then(setOv).catch((e: any) => setMsg(e.message || String(e))).finally(() => setLoading(false))
    apiGet<{ logs: string }>('/api/v1/security/logs/system?lines=30').then((r) => setSyslogs(r.logs)).catch(() => {})
    apiGet<{ logs: string }>('/api/v1/security/logs/firewall?lines=50').then((r) => setFwlogs(r.logs)).catch(() => {})
  }, [])
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Security Center (journald)</h2>
      <Msg text={msg} />
      {loading ? (
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="card"><Skeleton lines={2} /></div>
          ))}
        </div>
      ) : (
      <>
      <div className="grid grid-cols-3 gap-4">
        <Stat label="Échecs de connexion (24h)" value={String(ov?.failed_logins_24h ?? '…')} tone={ov?.failed_logins_24h > 0 ? 'warn' : 'ok'} />
        <Stat label="Alertes suspectes" value={String(ov?.suspicious?.length ?? '…')} tone={(ov?.suspicious?.length || 0) > 0 ? 'bad' : 'ok'} />
        <Stat label="Mises à jour en attente" value={String(ov?.updates_pending ?? '…')} tone={ov?.updates_pending > 0 ? 'warn' : 'ok'} />
      </div>
      <Card title="Activité suspecte">
        {(ov?.suspicious || []).map((s: any, i: number) => (
          <div key={i} className="text-sm text-red-300 py-0.5">[{s.rule}] {s.detail} <span className="text-slate-400">({s.ip})</span></div>
        ))}
        {(ov?.suspicious || []).length === 0 && <p className="text-sm text-green-400">Rien à signaler</p>}
      </Card>
      <Card title={`Derniers échecs de connexion (${(ov?.failed_logins || []).length})`}>
        {(ov?.failed_logins || []).slice(0, 8).map((e: any, i: number) => (
          <div key={i} className="text-xs py-0.5">{String(e.ts).slice(0, 19)} — <b>{e.actor}</b> depuis <span className="font-mono">{e.ip}</span> ({e.result})</div>
        ))}
      </Card>
      <Card title="Intégrations">
        {(ov?.integrations || []).map((it: any) => (
          <div key={it.name} className="text-sm py-1">{it.name} <span className="text-xs text-slate-400">{it.status} — {it.detail}</span></div>
        ))}
      </Card>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card title="Logs système (30 lignes)"><pre className="text-xs whitespace-pre-wrap">{syslogs.slice(-3000) || '…'}</pre></Card>
        <Card title="Logs pare-feu (noyau)"><pre className="text-xs whitespace-pre-wrap">{fwlogs.slice(-3000) || 'aucune entrée'}</pre></Card>
      </div>
      </>
      )}
    </div>
  )
}
