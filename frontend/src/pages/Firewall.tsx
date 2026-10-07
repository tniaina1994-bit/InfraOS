import React from 'react'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Table, Badge, Msg, Field, inputCls, Spinner } from '../components/ui'

export default function Firewall() {
  const [rules, setRules] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [nr, setNr] = React.useState({ name: '', chain: 'input', action: 'accept', proto: 'tcp', dport: 443 })
  async function load() {
    try { setRules((await apiGet<{ rules: any[] }>('/api/v1/firewall/rules')).rules) }
    catch (e: any) { setMsg(e.message || String(e)) }
    finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Firewall (nftables)</h2>
      <Msg text={msg} />
      {loading && <Spinner label="Chargement des règles…" />}
      {!loading && (
      <Card title="Règles" right={<button className="btn" onClick={() => apiCall('/api/v1/firewall/apply', 'POST').then((r: any) => setMsg(r.applied ? 'Règles appliquées (vérifiées)' : `Échec : ${(r.detail || '').slice(0, 200)}`)).catch((e: any) => setMsg(e.message))}>Appliquer (nft)</button>}>
        <Table
          rows={rules}
          keyOf={(r) => r.id}
          columns={[
            ['Nom', (r) => r.name],
            ['Chaîne', (r) => r.chain],
            ['Action', (r) => <Badge value={r.action} good={['accept']} bad={['drop']} />],
            ['Proto', (r) => r.proto],
            ['Port', (r) => r.dport || '—'],
            ['Source', (r) => <span className="font-mono">{r.src || '—'}</span>],
            ['NAT vers', (r) => <span className="font-mono">{r.nat_to || '—'}</span>],
            ['Action', (r) => <button className="btn" onClick={() => { if (confirm(`Supprimer ${r.name} ?`)) apiCall(`/api/v1/firewall/rules/${r.id}`, 'DELETE').then(load).catch((e: any) => setMsg(e.message)) }}>Supprimer</button>],
          ]}
        />
        <div className="flex gap-2 mt-3 flex-wrap items-end">
          <Field label="Nom"><input className={inputCls} value={nr.name} onChange={(e) => setNr({ ...nr, name: e.target.value })} /></Field>
          <Field label="Chaîne">
            <select className={inputCls} value={nr.chain} onChange={(e) => setNr({ ...nr, chain: e.target.value })}>
              {['input', 'forward', 'output', 'prerouting', 'postrouting'].map((c) => <option key={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Action">
            <select className={inputCls} value={nr.action} onChange={(e) => setNr({ ...nr, action: e.target.value })}>
              {['accept', 'drop', 'dnat', 'masquerade', 'log'].map((c) => <option key={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Proto">
            <select className={inputCls} value={nr.proto} onChange={(e) => setNr({ ...nr, proto: e.target.value })}>
              {['all', 'tcp', 'udp', 'icmp'].map((c) => <option key={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Port"><input className={inputCls} type="number" value={nr.dport} onChange={(e) => setNr({ ...nr, dport: Number(e.target.value) })} /></Field>
          <button className="btn" onClick={() => apiCall('/api/v1/firewall/rules', 'POST', nr).then(() => { setMsg('Règle ajoutée (pensez à Appliquer)'); load() }).catch((e: any) => setMsg(e.message))}>Ajouter</button>
        </div>
      </Card>
      )}
    </div>
  )
}
