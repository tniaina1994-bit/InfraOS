import React from 'react'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Table, Badge, Msg, Field, inputCls, Spinner, Skeleton } from '../components/ui'

export default function Shares() {
  const [shares, setShares] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [ns, setNs] = React.useState({ name: '', path: '' })
  async function load() {
    try { setShares((await apiGet<{ shares: any[] }>('/api/v1/shares/shares')).shares) }
    catch (e: any) { setMsg(e.message || String(e)) }
    finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Serveur de fichiers (Samba)</h2>
      <Msg text={msg} />
      {loading ? <div className="card"><Skeleton lines={3} /></div> : (
      <Card title="Partages" right={<button className="btn" onClick={() => apiCall('/api/v1/shares/apply', 'POST').then(() => setMsg('Samba appliqué (testparm + reload)')).catch((e: any) => setMsg(e.message))}>Appliquer (Samba)</button>}>
        <Table
          rows={shares}
          keyOf={(s) => s.id}
          columns={[
            ['Nom', (s) => `[${s.name}]`],
            ['Chemin', (s) => <span className="font-mono">{s.path}</span>],
            ['Commentaire', (s) => s.comment || '—'],
            ['Lecture seule', (s) => <Badge value={s.read_only ? 'oui' : 'non'} />],
            ['Action', (s) => <button className="btn" onClick={() => { if (confirm(`Supprimer ${s.name} ?`)) apiCall(`/api/v1/shares/shares/${s.id}`, 'DELETE').then(load).catch((e: any) => setMsg(e.message)) }}>Supprimer</button>],
          ]}
        />
        <div className="flex gap-2 mt-3 flex-wrap items-end">
          <Field label="Nom"><input className={inputCls} value={ns.name} onChange={(e) => setNs({ ...ns, name: e.target.value })} /></Field>
          <Field label="Chemin (/srv/…)"><input className={inputCls} value={ns.path} onChange={(e) => setNs({ ...ns, path: e.target.value })} /></Field>
          <button className="btn" onClick={() => apiCall('/api/v1/shares/shares', 'POST', ns).then(() => { setNs({ name: '', path: '' }); setMsg('Partage créé'); load() }).catch((e: any) => setMsg(e.message))}>Créer</button>
        </div>
      </Card>
      )}
    </div>
  )
}
