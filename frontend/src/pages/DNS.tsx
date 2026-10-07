import React from 'react'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Table, Badge, Msg, Field, inputCls, Spinner } from '../components/ui'

const RTYPES = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'PTR', 'NS']

export default function DNS() {
  const [zones, setZones] = React.useState<any[]>([])
  const [sel, setSel] = React.useState('')
  const [records, setRecords] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [loadingRecords, setLoadingRecords] = React.useState(false)
  const [msg, setMsg] = React.useState('')
  const [nz, setNz] = React.useState('')
  const [nr, setNr] = React.useState({ name: '', rtype: 'A', value: '' })

  async function loadZones() {
    try {
      const d = await apiGet<{ zones: any[] }>('/api/v1/dns/zones')
      setZones(d.zones)
    } catch (e: any) {
      setMsg(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  async function loadRecords(z: string) {
    setSel(z)
    setLoadingRecords(true)
    try {
      const d = await apiGet<{ records: any[] }>(`/api/v1/dns/zones/${z}/records`)
      setRecords(d.records)
    } catch (e: any) {
      setMsg(e.message || String(e))
    } finally {
      setLoadingRecords(false)
    }
  }

  async function apply() {
    try {
      const r: any = await apiCall('/api/v1/dns/apply', 'POST')
      setMsg(r.applied ? 'Appliqué dans BIND9' : 'Échec, voir les logs')
    } catch (e: any) {
      setMsg(e.message || String(e))
    }
  }

  async function createZone() {
    try {
      await apiCall('/api/v1/dns/zones', 'POST', { name: nz })
      setNz('')
      setMsg('Zone créée')
      loadZones()
    } catch (e: any) {
      setMsg(e.message || String(e))
    }
  }

  async function delZone(name: string) {
    if (!confirm(`Supprimer ${name} ?`)) return
    try {
      await apiCall(`/api/v1/dns/zones/${name}`, 'DELETE')
      loadZones()
    } catch (e: any) {
      setMsg(e.message || String(e))
    }
  }

  async function addRecord() {
    try {
      await apiCall(`/api/v1/dns/zones/${sel}/records`, 'POST', nr)
      setNr({ name: '', rtype: 'A', value: '' })
      loadRecords(sel)
    } catch (e: any) {
      setMsg(e.message || String(e))
    }
  }

  async function delRecord(id: number) {
    try {
      await apiCall(`/api/v1/dns/records/${id}`, 'DELETE')
      loadRecords(sel)
    } catch (e: any) {
      setMsg(e.message || String(e))
    }
  }

  React.useEffect(() => { loadZones() }, [])

  function zoneRows() {
    return zones.map((z) => ({
      name: z.name,
      kind: z.reverse ? `${z.kind} (reverse)` : z.kind,
      ttl: String(z.ttl),
      enabled: z.enabled,
    }))
  }

  function recordRows() {
    return records.map((r) => ({
      id: r.id,
      name: r.name,
      rtype: r.rtype,
      value: r.rtype === 'MX' ? `${r.value} (priorité ${r.priority})` : r.value,
    }))
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">DNS Manager (BIND9)</h2>
      <Msg text={msg} />
      {loading && <Spinner label="Chargement des zones…" />}
      {!loading && (
        <Card title="Zones" right={<button className="btn" onClick={apply}>Appliquer (BIND9)</button>}>
          <Table
            rows={zoneRows()}
            keyOf={(z) => z.name}
            columns={[
              ['Zone', (z) => <button key="n" className="underline" onClick={() => loadRecords(z.name)}>{z.name}</button>],
              ['Type', (z) => <span key="t">{z.kind}</span>],
              ['TTL', (z) => <span key="l">{z.ttl}</span>],
              ['État', (z) => <Badge key="e" value={z.enabled ? 'activée' : 'désactivée'} good={['activée']} />],
              ['Action', (z) => <button key="a" className="btn" onClick={() => delZone(z.name)}>Supprimer</button>],
            ]}
          />
          <div className="flex gap-2 mt-3 items-end">
            <Field label="Nouvelle zone (ex. lan.local)">
              <input className={inputCls} value={nz} onChange={(e) => setNz(e.target.value)} />
            </Field>
            <button className="btn" onClick={createZone}>Créer</button>
          </div>
        </Card>
      )}
      {!loading && sel !== '' && (
        <Card title={`Enregistrements de ${sel}`}>
          {loadingRecords ? (
            <Spinner label="Chargement…" />
          ) : (
            <Table
              rows={recordRows()}
              keyOf={(r) => r.id}
              columns={[
                ['Nom', (r) => <span key="n">{r.name}</span>],
                ['Type', (r) => <Badge key="t" value={r.rtype} />],
                ['Valeur', (r) => <span key="v" className="font-mono">{r.value}</span>],
                ['Action', (r) => <button key="a" className="btn" onClick={() => delRecord(r.id)}>Supprimer</button>],
              ]}
            />
          )}
          <div className="flex gap-2 mt-3 flex-wrap items-end">
            <Field label="Nom">
              <input className={inputCls} value={nr.name} onChange={(e) => setNr({ ...nr, name: e.target.value })} />
            </Field>
            <Field label="Type">
              <select className={inputCls} value={nr.rtype} onChange={(e) => setNr({ ...nr, rtype: e.target.value })}>
                {RTYPES.map((t) => <option key={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="Valeur">
              <input className={inputCls} value={nr.value} onChange={(e) => setNr({ ...nr, value: e.target.value })} />
            </Field>
            <button className="btn" onClick={addRecord}>Ajouter</button>
          </div>
        </Card>
      )}
    </div>
  )
}
