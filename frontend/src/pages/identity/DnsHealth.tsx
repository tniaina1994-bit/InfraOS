import React from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../../lib/api'
import { apiCall } from '../../lib/client'
import { Card, Table, Badge, Msg, Field, inputCls, Spinner, Stat, Empty } from '../../components/ui'

export default function IdentityDnsHealth() {
  const [info, setInfo] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [q, setQ] = React.useState({ name: '', rtype: 'SRV' })
  const [qres, setQres] = React.useState<any>(null)

  const load = () => apiGet<any>('/api/v1/identity/domain/dns')
    .then(setInfo).catch((e) => setMsg(String(e))).finally(() => setLoading(false))
  React.useEffect(() => { load() }, [])

  async function lookup() {
    setMsg(''); setQres(null)
    try {
      setQres(await apiGet<any>(
        `/api/v1/identity/test/dns?name=${encodeURIComponent(q.name)}&rtype=${q.rtype}`))
    } catch (e: any) { setMsg(e.message || String(e)) }
  }

  if (loading) return <Spinner label="Chargement DNS de domaine…" />
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">DNS Health (domaine)</h2>
        <Link className="btn" to="/identity">← Vue d'ensemble</Link>
      </div>
      <Msg text={msg} />
      {info && !info.provisioned && (
        <div className="card border-yellow-700 bg-yellow-900/20 text-sm text-yellow-300">
          {info.detail} — <Link className="underline" to="/identity/domain">créer le domaine</Link>
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Statut" value={info?.status || '—'}
          tone={info?.status === 'healthy' ? 'ok' : info?.status === 'degraded' ? 'warn' : 'bad'} />
        <Stat label="Zone" value={info?.zone || '—'} />
        <Stat label="Forward" value={info?.forward?.resolved ? 'OK' : 'NXDOMAIN'}
          tone={info?.forward?.resolved ? 'ok' : 'warn'} />
        <Stat label="Reverse (PTR)" value={info?.reverse?.resolved ? 'OK' : 'absent'}
          tone={info?.reverse?.resolved ? 'ok' : 'warn'} />
      </div>
      {info?.zones?.length > 0 && (
        <Card title="Zones">
          <div className="flex flex-wrap gap-2">
            {info.zones.map((z: string) => (
              <span key={z} className="px-2 py-1 rounded bg-slate-800 text-sm">{z}</span>
            ))}
          </div>
        </Card>
      )}
      <Card title="Enregistrements critiques (SRV/A)">
        <Table rows={info?.records || []} keyOf={(r: any) => `${r.name}-${r.type}`}
          columns={[
            ['Nom', (r: any) => <span className="text-xs break-all">{r.name}</span>],
            ['Type', (r: any) => r.type],
            ['État', (r: any) => <Badge value={r.status} good={['PASS']} bad={['ERROR']} />],
            ['Détail', (r: any) => <span className="text-xs break-all">{r.detail}</span>],
          ]} />
        {info?.provisioned && !(info.records || []).length && <Empty text="Aucun enregistrement" />}
      </Card>
      <Card title="Interroger le DNS de domaine">
        <div className="flex gap-3 items-end flex-wrap">
          <Field label="Nom (ex. _ldap._tcp)">
            <input className={inputCls} value={q.name}
              onChange={(e) => setQ({ ...q, name: e.target.value })} />
          </Field>
          <Field label="Type">
            <select className={inputCls} value={q.rtype}
              onChange={(e) => setQ({ ...q, rtype: e.target.value })}>
              {['SRV', 'A', 'AAAA', 'PTR', 'CNAME', 'MX', 'NS', 'SOA', 'TXT', 'ALL']
                .map((t) => <option key={t}>{t}</option>)}
            </select>
          </Field>
          <button className="btn" disabled={!q.name} onClick={lookup}>Rechercher</button>
        </div>
        {qres && (
          <pre className="text-xs mt-3 whitespace-pre-wrap break-all">{qres.output}</pre>
        )}
      </Card>
    </div>
  )
}
