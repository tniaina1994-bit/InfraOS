import React from 'react'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Table, Msg, Field, inputCls, Spinner, Skeleton } from '../components/ui'

export default function IPAM() {
  const [nets, setNets] = React.useState<any[]>([])
  const [usage, setUsage] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [nn, setNn] = React.useState({ name: '', cidr: '', gateway: '' })
  const [nh, setNh] = React.useState({ hostname: '' })
  async function load() {
    try { setNets((await apiGet<{ networks: any[] }>('/api/v1/ipam/networks')).networks) }
    catch (e: any) { setMsg(e.message || String(e)) }
    finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])
  async function show(nid: number) {
    try { setUsage(await apiGet(`/api/v1/ipam/networks/${nid}`)) }
    catch (e: any) { setMsg(e.message || String(e)) }
  }
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">IPAM</h2>
      <Msg text={msg} />
      {loading ? <div className="card"><Skeleton lines={3} /></div> : (
        <>
          <Card title="Réseaux">
            <Table
              rows={nets}
              keyOf={(n) => n.id}
              columns={[
                ['Nom', (n) => <button className="underline" onClick={() => show(n.id)}>{n.name}</button>],
                ['CIDR', (n) => <span className="font-mono">{n.cidr}</span>],
                ['Passerelle', (n) => <span className="font-mono">{n.gateway || '—'}</span>],
                ['VLAN', (n) => n.vlan || '—'],
              ]}
            />
            <div className="flex gap-2 mt-3 flex-wrap items-end">
              <Field label="Nom"><input className={inputCls} value={nn.name} onChange={(e) => setNn({ ...nn, name: e.target.value })} /></Field>
              <Field label="CIDR"><input className={inputCls} placeholder="192.168.20.0/24" value={nn.cidr} onChange={(e) => setNn({ ...nn, cidr: e.target.value })} /></Field>
              <Field label="Passerelle"><input className={inputCls} value={nn.gateway} onChange={(e) => setNn({ ...nn, gateway: e.target.value })} /></Field>
              <button className="btn" onClick={() => apiCall('/api/v1/ipam/networks', 'POST', nn).then(() => { setNn({ name: '', cidr: '', gateway: '' }); load() }).catch((e: any) => setMsg(e.message))}>Créer</button>
            </div>
          </Card>
          {usage && (
            <Card title={`Utilisation ${usage.network} — ${usage.used}/${usage.total} (${usage.free} libres)`}>
              <div className="h-2 rounded bg-slate-800 mb-3">
                <div className="h-2 rounded bg-blue-500" style={{ width: `${Math.round((usage.used / Math.max(usage.total, 1)) * 100)}%` }} />
              </div>
              <Table
                rows={usage.hosts}
                keyOf={(h: any, i: number) => `${h.ip}-${i}`}
                columns={[
                  ['IP', (h) => <span className="font-mono">{h.ip}</span>],
                  ['Hôte', (h) => h.hostname || '—'],
                  ['MAC', (h) => <span className="font-mono">{h.mac || '—'}</span>],
                  ['Type', (h) => h.kind],
                ]}
              />
              <div className="flex gap-2 mt-3 items-end">
                <Field label="Nom d'hôte (allocation auto)">
                  <input className={inputCls} value={nh.hostname} onChange={(e) => setNh({ hostname: e.target.value })} />
                </Field>
                <button className="btn" onClick={() => {
                  const nid = nets.find((n) => n.cidr === usage.network)?.id
                  if (!nid) return
                  apiCall(`/api/v1/ipam/networks/${nid}/hosts`, 'POST', { hostname: nh.hostname }).then(() => { setNh({ hostname: '' }); show(nid) }).catch((e: any) => setMsg(e.message))
                }}>Allouer</button>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  )
}