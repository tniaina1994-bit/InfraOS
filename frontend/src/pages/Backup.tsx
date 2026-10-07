import React from 'react'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Table, Badge, Msg, Field, inputCls, Spinner, Skeleton } from '../components/ui'

export default function Backup() {
  const [jobs, setJobs] = React.useState<any[]>([])
  const [runs, setRuns] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [nj, setNj] = React.useState({ name: '', backend: 'restic', repo: '', sources: '' })
  async function load() {
    try { setJobs((await apiGet<{ jobs: any[] }>('/api/v1/backup/jobs')).jobs) }
    catch (e: any) { setMsg(e.message || String(e)) }
    finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Sauvegardes (restic / borg / rsync)</h2>
      <Msg text={msg} />
      {loading ? <div className="card"><Skeleton lines={3} /></div> : (
        <>
          <Card title="Tâches">
            <Table
              rows={jobs}
              keyOf={(j) => j.id}
              columns={[
                ['Nom', (j) => j.name],
                ['Moteur', (j) => <Badge value={j.backend} />],
                ['Dépôt', (j) => <span className="font-mono">{j.repo}</span>],
                ['Planification', (j) => <span className="font-mono">{j.schedule || 'manuelle'}</span>],
                ['Rétention', (j) => <span className="font-mono">{j.retention}</span>],
                ['Chiffré', (j) => <Badge value={j.encrypted ? 'oui' : 'non'} good={['oui']} bad={['non']} />],
                ['Activé', (j) => <Badge value={j.enabled ? 'oui' : 'non'} good={['oui']} bad={['non']} />],
                ['Action', (j) => <button className="btn" onClick={() => { setMsg(`Sauvegarde ${j.name} en cours…`); apiCall(`/api/v1/backup/jobs/${j.id}/run`, 'POST').then((r: any) => setMsg(`Exécution ${r.run_id} : ${r.status}`)).catch((e: any) => setMsg(e.message)) }}>Exécuter</button>],
              ]}
            />
            <div className="flex gap-2 mt-3 flex-wrap items-end">
              <Field label="Nom"><input className={inputCls} value={nj.name} onChange={(e) => setNj({ ...nj, name: e.target.value })} /></Field>
              <Field label="Moteur">
                <select className={inputCls} value={nj.backend} onChange={(e) => setNj({ ...nj, backend: e.target.value })}>
                  {['restic', 'borg', 'rsync'].map((b) => <option key={b}>{b}</option>)}
                </select>
              </Field>
              <Field label="Dépôt"><input className={inputCls} value={nj.repo} onChange={(e) => setNj({ ...nj, repo: e.target.value })} /></Field>
              <Field label="Sources (séparées par ,)"><input className={inputCls} value={nj.sources} onChange={(e) => setNj({ ...nj, sources: e.target.value })} /></Field>
              <button className="btn" onClick={() => apiCall('/api/v1/backup/jobs', 'POST', { ...nj, sources: nj.sources.split(',').map((s) => s.trim()).filter(Boolean) }).then(() => { setNj({ name: '', backend: 'restic', repo: '', sources: '' }); load() }).catch((e: any) => setMsg(e.message))}>Créer</button>
            </div>
          </Card>
          {runs.length > 0 && (
            <Card title="Dernières exécutions">
              <Table
                rows={runs}
                keyOf={(r) => r.id}
                columns={[
                  ['#', (r) => r.id],
                  ['Statut', (r) => <Badge value={r.status} good={['done']} bad={['error']} />],
                  ['Début', (r) => String(r.created_at).slice(0, 19)],
                  ['Fin', (r) => r.finished_at ? String(r.finished_at).slice(0, 19) : '—'],
                ]}
              />
            </Card>
          )}
        </>
      )}
    </div>
  )
}