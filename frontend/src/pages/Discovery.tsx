import React from 'react'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Table, Msg, Field, inputCls, Spinner } from '../components/ui'

export default function Discovery() {
  const [scans, setScans] = React.useState<any[]>([])
  const [hosts, setHosts] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [scanning, setScanning] = React.useState(false)
  const [msg, setMsg] = React.useState('')
  const [target, setTarget] = React.useState('192.168.10.0/24')
  const [profile, setProfile] = React.useState('ping')
  async function load() {
    try { setScans((await apiGet<{ scans: any[] }>('/api/v1/discovery/scans')).scans) }
    catch (e: any) { setMsg(e.message || String(e)) }
    finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Découverte réseau <span className="text-sm font-normal text-slate-400">(lancement manuel uniquement)</span></h2>
      <Msg text={msg} />
      {loading && <Spinner label="Chargement de l'historique…" />}
      {!loading && (
      <>
      <Card title="Nouveau scan">
        <div className="flex gap-2 flex-wrap items-end">
          <Field label="Cible (CIDR ≥ /16 ou IP)">
            <input className={inputCls} value={target} onChange={(e) => setTarget(e.target.value)} />
          </Field>
          <Field label="Profil">
            <select className={inputCls} value={profile} onChange={(e) => setProfile(e.target.value)}>
              <option value="ping">ping — hôtes + MAC</option>
              <option value="fast">fast — ports courants</option>
              <option value="os">os — système (1 hôte)</option>
            </select>
          </Field>
          <button className="btn" disabled={scanning} onClick={() => { setScanning(true); setMsg('Scan en cours…'); apiCall('/api/v1/discovery/scans', 'POST', { target, profile }).then((r: any) => { setHosts(r.hosts); setMsg(`${r.hosts_up} hôtes découverts`); load() }).catch((e: any) => setMsg(e.message)).finally(() => setScanning(false)) }}>{scanning ? 'Scan…' : 'Scanner'}</button>
        </div>
        {hosts.length > 0 && (
          <div className="mt-3">
            <Table
              rows={hosts}
              keyOf={(h) => h.ip}
              columns={[
                ['IP', (h) => <span className="font-mono">{h.ip}</span>],
                ['MAC', (h) => <span className="font-mono">{h.mac || '—'}</span>],
                ['Hôte', (h) => h.hostname || '—'],
                ['Ports ouverts', (h) => (h.ports || []).map((p: any) => `${p.port}/${p.proto}`).join(', ') || '—'],
                ['OS', (h) => h.os || '—'],
              ]}
            />
          </div>
        )}
      </Card>
      <Card title="Scans précédents">
        <Table
          rows={scans}
          keyOf={(s) => s.id}
          columns={[
            ['#', (s) => s.id],
            ['Cible', (s) => <span className="font-mono">{s.target}</span>],
            ['Profil', (s) => s.profile],
            ['Hôtes', (s) => s.hosts_up],
            ['Date', (s) => String(s.created_at).slice(0, 19)],
            ['Voir', (s) => <button className="btn" onClick={() => apiCall(`/api/v1/discovery/scans/${s.id}`).then((r: any) => setHosts(r.hosts)).catch((e: any) => setMsg(e.message))}>Voir</button>],
          ]}
        />
      </Card>
      </>
      )}
    </div>
  )
}
