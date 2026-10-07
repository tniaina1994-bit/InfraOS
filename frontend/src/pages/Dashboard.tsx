import React from 'react'
import { apiGet } from '../lib/api'
import { Stat, Card, Badge, Msg, Spinner, Skeleton } from '../components/ui'

export default function Dashboard() {
  const [d, setD] = React.useState<any>({})
  const [loading, setLoading] = React.useState(true)
  const [err, setErr] = React.useState('')
  React.useEffect(() => {
    (async () => {
      try {
        const [health, info, services, modules, syshealth, updates, sec, net] = await Promise.all([
          apiGet<any>('/api/health'),
          apiGet<any>('/api/v1/system/info'),
          apiGet<any>('/api/v1/services'),
          apiGet<any>('/api/v1/modules'),
          apiGet<any>('/api/v1/system/health'),
          apiGet<any>('/api/v1/updates'),
          apiGet<any>('/api/v1/security/overview'),
          apiGet<any>('/api/v1/network/interfaces'),
        ])
        setD({ health, info, services, modules, syshealth, updates, sec, net })
        setLoading(false)
      } catch (e: any) { setErr(e.message || String(e)); setLoading(false) }
    })()
  }, [])
  const active = (d.services?.services || []).filter((s: any) => s.active === 'active')
  const upIfs = (d.net?.interfaces || []).filter((i: any) => i.up && i.name !== 'lo')
  const tone = (v: string) => v === 'ok' ? 'ok' as const : v === 'degraded' ? 'warn' as const : undefined
  if (loading && !err) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <Spinner label="Chargement du tableau de bord…" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="card"><Skeleton lines={2} /></div>
          ))}
        </div>
      </div>
    )
  }
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Dashboard</h2>
      {err && <div className="card text-red-300">API inaccessible : {err} — connectez-vous via Connexion</div>}
      {!err && (
      <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Version" value={d.health ? `${d.health.service} ${d.health.version}` : '…'} />
        <Stat label="Hôte" value={d.info?.hostname || '…'} />
        <Stat label="OS" value={d.info?.pretty?.replace('Debian GNU/Linux ', '') || '…'} />
        <Stat label="Santé" value={d.syshealth?.status || '…'} tone={d.syshealth ? tone(d.syshealth.status) : undefined} />
        <Stat label="CPU" value={d.info?.cpu_percent != null ? `${d.info.cpu_percent} %` : '…'} />
        <Stat label="RAM" value={d.info?.mem ? `${d.info.mem.percent} %` : '…'} />
        <Stat label="Disque" value={d.info?.disk ? `${d.info.disk.percent} %` : '…'} />
        <Stat label="Mises à jour" value={String(d.updates?.pending ?? '…')} tone={d.updates?.pending > 0 ? 'warn' : 'ok'} />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card title={`Services actifs (${active.length})`}>
          <div className="flex flex-wrap gap-2">
            {active.map((s: any) => <Badge key={s.name} value={s.name} good={[s.name]} />)}
            {active.length === 0 && <span className="text-sm text-slate-400">…</span>}
          </div>
        </Card>
        <Card title={`Réseau (${upIfs.map((i: any) => i.name).join(', ') || '…'}` + ')'}>
          <div className="text-sm space-y-1">
            {(d.net?.interfaces || []).filter((i: any) => i.up).map((i: any) => (
              <div key={i.name}>{i.name} — {(i.addresses || []).filter((a: any) => a.family === '2').map((a: any) => a.address).join(', ')}</div>
            ))}
          </div>
        </Card>
        <Card title={`Modules (${d.modules?.count ?? '…'})`}>
          <span className="text-sm text-slate-300">{d.modules ? 'tous opérationnels' : '…'}</span>
        </Card>
        <Card title={`Échecs de connexion (24h) : ${d.sec?.failed_logins_24h ?? '…'}`}>
          {(d.sec?.suspicious || []).map((s: any, i: number) => (
            <div key={i} className="text-sm text-red-300">[{s.rule}] {s.detail}</div>
          ))}
          {(d.sec?.suspicious || []).length === 0 && <p className="text-sm text-green-400">Rien à signaler</p>}
        </Card>
      </div>
      </>
      )}
    </div>
  )
}
