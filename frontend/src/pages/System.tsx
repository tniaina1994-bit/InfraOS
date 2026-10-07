import React from 'react'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Table, Badge, Msg, Spinner, Skeleton } from '../components/ui'

const HEALTH_LABEL: Record<string, string> = {
  db: 'Base de données', cache: 'Cache', disk: 'Disque', memory: 'Mémoire', services: 'Services critiques',
}

export default function System() {
  const [info, setInfo] = React.useState<any>(null)
  const [health, setHealth] = React.useState<any>(null)
  const [services, setServices] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  async function load() {
    try {
      setInfo(await apiGet('/api/v1/system/info'))
      setHealth(await apiGet('/api/v1/system/health'))
      setServices((await apiGet<{ services: any[] }>('/api/v1/services')).services)
    } catch (e: any) { setMsg(e.message || String(e)) }
    finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])
  async function act(name: string, action: string) {
    if (!confirm(`${action} ${name} ? (admin)`)) return
    try {
      const r = await apiCall(`/api/v1/services/${name}/${action}`, 'POST')
      setMsg(`${action} ${name} : ${r.rc === 0 ? 'OK' : 'code ' + r.rc}`)
      await load()
    } catch (e: any) { setMsg(e.message || String(e)) }
  }
  const checks = health ? Object.entries(health.checks || {}) : []
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Système</h2>
      <Msg text={msg} />
      {loading && <Spinner label="Chargement du système…" />}
      {!loading && (
      <>
      <Card title={`Santé : ${health?.status || '…'}`}>
        <div className="space-y-1">
          {checks.map(([k, v]: [string, any]) => (
            <div key={k} className="flex gap-2 text-sm">
              <Badge value={v.status} good={['ok']} bad={['fail']} />
              <span className="w-40">{HEALTH_LABEL[k] || k}</span>
              <span className="text-slate-400">{v.detail}</span>
            </div>
          ))}
        </div>
      </Card>
      <Card title="Services">
        <Table
          rows={services}
          keyOf={(s) => s.name}
          columns={[
            ['Service', (s) => s.name],
            ['État', (s) => <Badge value={s.active} good={['active']} bad={['failed', 'inactive']} />],
            ['Actions', (s) => (
              <span className="flex gap-1">
                {!['active'].includes(s.active) && (
                  <button key="start" className="btn bg-green-600 hover:bg-green-500" onClick={() => act(s.name, 'start')}>start</button>
                )}
                {['restart', 'stop'].map((a) => (
                  <button key={a} className="btn" onClick={() => act(s.name, a)}>{a}</button>
                ))}
              </span>
            )],
          ]}
        />
        <p className="text-xs text-slate-500 mt-2">Actions réservées au rôle admin, auditées.</p>
      </Card>
      <Card title="Informations">
        {info && (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm max-w-xl">
            {[['Hôte', info.hostname], ['OS', info.pretty], ['Noyau', info.kernel], ['Arch', info.arch],
              ['Python', info.python], ['Virt', info.virt],
              ['CPU', `${info.cpu_percent} %`],
              ['Mémoire', `${info.mem?.percent} %`],
              ['Disque', `${info.disk?.percent} % (${Math.round((info.disk?.free || 0) / 1e9)} Go libres)`],
            ].map(([k, v]) => (
              <React.Fragment key={k as string}>
                <dt className="text-slate-400">{k}</dt><dd>{v}</dd>
              </React.Fragment>
            ))}
          </dl>
        )}
      </Card>
      </>
      )}
    </div>
  )
}
