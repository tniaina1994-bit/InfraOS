import React from 'react'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Table, Msg, Field, inputCls, Spinner } from '../components/ui'

export default function DHCP() {
  const [scopes, setScopes] = React.useState<any[]>([])
  const [leases, setLeases] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [ns, setNs] = React.useState({ name: '', subnet: '', pool_start: '', pool_end: '', gateway: '' })
  async function load() {
    try {
      setScopes((await apiGet<{ scopes: any[] }>('/api/v1/dhcp/scopes')).scopes)
      setLeases((await apiGet<{ leases: any[] }>('/api/v1/dhcp/leases')).leases)
    } catch (e: any) { setMsg(e.message || String(e)) }
    finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">DHCP Manager (Kea)</h2>
      <Msg text={msg} />
      {loading && <Spinner label="Chargement du DHCP…" />}
      {!loading && (
      <>
      <Card title="Scopes" right={<button className="btn" onClick={() => apiCall('/api/v1/dhcp/apply', 'POST').then((r: any) => setMsg(r.applied ? 'Kea appliqué et redémarré' : `Échec : ${(r.detail || '').slice(0, 200)}`)).catch((e: any) => setMsg(e.message))}>Appliquer (Kea)</button>}>
        <Table
          rows={scopes}
          keyOf={(s) => s.id}
          columns={[
            ['Nom', (s) => s.name],
            ['Sous-réseau', (s) => <span className="font-mono">{s.subnet}</span>],
            ['Plage', (s) => <span className="font-mono">{s.pool_start} – {s.pool_end}</span>],
            ['Passerelle', (s) => s.gateway || '—'],
            ['DNS', (s) => (s.dns || []).join(', ') || '—'],
            ['Baux (s)', (s) => `${s.lease_valid} / ${s.lease_max}`],
          ]}
        />
        <div className="flex gap-2 mt-3 flex-wrap items-end">
          <Field label="Nom"><input className={inputCls} value={ns.name} onChange={(e) => setNs({ ...ns, name: e.target.value })} /></Field>
          <Field label="Sous-réseau"><input className={inputCls} placeholder="192.168.20.0/24" value={ns.subnet} onChange={(e) => setNs({ ...ns, subnet: e.target.value })} /></Field>
          <Field label="Début plage"><input className={inputCls} value={ns.pool_start} onChange={(e) => setNs({ ...ns, pool_start: e.target.value })} /></Field>
          <Field label="Fin plage"><input className={inputCls} value={ns.pool_end} onChange={(e) => setNs({ ...ns, pool_end: e.target.value })} /></Field>
          <Field label="Passerelle"><input className={inputCls} value={ns.gateway} onChange={(e) => setNs({ ...ns, gateway: e.target.value })} /></Field>
          <button className="btn" onClick={() => apiCall('/api/v1/dhcp/scopes', 'POST', ns).then(() => { setNs({ name: '', subnet: '', pool_start: '', pool_end: '', gateway: '' }); setMsg('Scope créé'); load() }).catch((e: any) => setMsg(e.message))}>Créer</button>
        </div>
      </Card>
      <Card title={`Baux actifs (${leases.length})`}>
        <Table
          rows={leases}
          keyOf={(l, i) => `${l.ip}-${i}`}
          columns={[
            ['IP', (l) => <span className="font-mono">{l.ip}</span>],
            ['MAC', (l) => <span className="font-mono">{l.mac}</span>],
            ['Hôte', (l) => l.hostname || '—'],
          ]}
        />
      </Card>
      </>
      )}
    </div>
  )
}
