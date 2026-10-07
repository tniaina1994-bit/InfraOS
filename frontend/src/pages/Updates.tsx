import React from 'react'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Table, Badge, Msg, Skeleton, Field, inputCls } from '../components/ui'

export default function Updates() {
  const [pending, setPending] = React.useState<any>(null)
  const [list, setList] = React.useState<any[]>([])
  const [hist, setHist] = React.useState<any[]>([])
  const [sources, setSources] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [showSources, setShowSources] = React.useState(false)
  const [newSource, setNewSource] = React.useState({ name: '', url: '', suite: '', components: '', key_url: '' })

  async function load() {
    try {
      setPending(await apiGet('/api/v1/updates'))
      setList((await apiGet<{ detail: any[] }>('/api/v1/updates/list')).detail || [])
      setHist((await apiGet<{ runs: any[] }>('/api/v1/updates/history')).runs)
      setSources((await apiGet<{ sources: any[] }>('/api/v1/updates/sources')).sources || [])
    } catch (e: any) { setMsg(e.message || String(e)) }
    finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])

  async function doFullUpgrade() {
    if (!confirm('Lancer une mise à jour complète du système (apt full-upgrade) ?\nLes paquets obsolètes seront installés/supprimés.')) return
    try {
      setMsg('Mise à jour complète en cours… (peut prendre plusieurs minutes)')
      const r = await apiCall('/api/v1/updates/full-upgrade', 'POST')
      setMsg('Mise à jour terminée : ' + (r.status || 'OK') + (r.detail ? ` — ${String(r.detail).slice(-300)}` : ''))
      load()
    } catch (e: any) { setMsg(e.message || String(e)) }
  }

  async function addSource() {
    if (!newSource.name || !newSource.url) { setMsg('Nom et URL requis'); return }
    try {
      await apiCall('/api/v1/updates/sources', 'POST', newSource)
      setMsg(`Source « ${newSource.name} » ajoutée`)
      setNewSource({ name: '', url: '', suite: '', components: '', key_url: '' })
      load()
    } catch (e: any) { setMsg(e.message || String(e)) }
  }

  async function removeSource(name: string) {
    if (!confirm(`Supprimer la source « ${name} » ?`)) return
    try {
      await apiCall(`/api/v1/updates/sources/${name}`, 'DELETE')
      setMsg(`Source « ${name} » supprimée`)
      load()
    } catch (e: any) { setMsg(e.message || String(e)) }
  }

  async function installPkg(name: string) {
    if (!confirm(`Installer ${name} ?`)) return
    try {
      await apiCall('/api/v1/updates/install', 'POST', { packages: [name] })
      setMsg(`${name} installé`)
      load()
    } catch (e: any) { setMsg(e.message || String(e)) }
  }

  const srcColumns: [string, (s: any) => React.ReactNode][] = [
    ['Nom', (s) => <span className="font-mono">{s.name}</span>],
    ['URL', (s) => <span className="font-mono text-xs break-all">{s.uri}</span>],
    ['Suite', (s) => s.suite || '—'],
    ['Composants', (s) => s.components || '—'],
    ['Signée', (s) => <Badge value={s.signed ? 'oui' : 'non'} good={['oui']} bad={['non']} />],
    ['Action', (s) => s.managed
      ? <button className="btn text-red-400 hover:bg-red-900" onClick={() => removeSource(s.name)}>Supprimer</button>
      : <span className="text-xs text-slate-500">système</span>],
  ]

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Mises à jour (APT — base Debian, jamais remplacée)</h2>
      <div className="flex gap-2 flex-wrap">
        <button className="btn bg-blue-600 hover:bg-blue-500" onClick={doFullUpgrade} disabled={loading}>
          Mise à jour complète (full-upgrade)
        </button>
        <button className="btn" onClick={() => setShowSources(!showSources)}>
          {showSources ? 'Masquer les sources APT' : 'Gérer les sources APT'}
        </button>
        <button className="btn" onClick={load} disabled={loading}>Rafraîchir</button>
      </div>
      <Msg text={msg} />
      {loading ? (
        <div className="card"><Skeleton lines={5} /></div>
      ) : (
        <div className="space-y-4">
          <Card title={`Paquets en attente : ${pending?.pending ?? '…'}`}>
            <Table
              rows={list.slice(0, 30)}
              keyOf={(p: any, i: number) => `${p.name}-${i}`}
              columns={[
                ['Paquet', (p) => <span className="font-mono">{p.name}</span>],
                ['Détail', (p) => <span className="text-xs text-slate-400">{p.info}</span>],
                ['Action', (p) => <button className="btn" onClick={() => installPkg(p.name)}>Installer</button>],
              ]}
            />
            {pending?.truncated && <p className="text-xs text-slate-400 mt-2">Liste tronquée (30 premiers).</p>}
          </Card>
          {showSources && (
            <Card title="Sources APT">
              <div className="mb-4">
                <h3 className="font-semibold mb-2">Sources existantes</h3>
                <Table rows={sources} keyOf={(s: any) => s.name} columns={srcColumns} />
              </div>
              <div className="p-3 border border-slate-700 rounded bg-slate-900/50">
                <h4 className="font-semibold mb-2">Ajouter une source APT</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <Field label="Nom (ex: docker, nginx)">
                    <input className={inputCls} value={newSource.name} onChange={(e) => setNewSource({ ...newSource, name: e.target.value })} placeholder="nom" />
                  </Field>
                  <Field label="URL du dépôt (ex: https://download.docker.com/linux/debian)">
                    <input className={inputCls} value={newSource.url} onChange={(e) => setNewSource({ ...newSource, url: e.target.value })} />
                  </Field>
                  <Field label="Suite (ex: bookworm, stable)">
                    <input className={inputCls} value={newSource.suite} onChange={(e) => setNewSource({ ...newSource, suite: e.target.value })} />
                  </Field>
                  <Field label="Composants (ex: main, stable)">
                    <input className={inputCls} value={newSource.components} onChange={(e) => setNewSource({ ...newSource, components: e.target.value })} />
                  </Field>
                  <Field label="URL de la clé GPG (optionnel, https)">
                    <input className={inputCls} value={newSource.key_url} onChange={(e) => setNewSource({ ...newSource, key_url: e.target.value })} placeholder="https://…/gpg" />
                  </Field>
                </div>
                <button className="btn mt-3" onClick={addSource}>Ajouter la source</button>
              </div>
            </Card>
          )}
          <Card title="Historique des installations">
            <Table
              rows={hist}
              keyOf={(r: any) => r.id}
              columns={[
                ['#', (r) => r.id],
                ['Type', (r) => r.kind],
                ['Paquets', (r) => <span className="font-mono text-xs">{(r.packages || []).join(', ') || '—'}</span>],
                ['Statut', (r) => <Badge value={r.status} good={['done']} bad={['error', 'running']} />],
                ['Par', (r) => r.actor],
                ['Date', (r) => String(r.created_at).slice(0, 19)],
              ]}
            />
          </Card>
        </div>
      )}
    </div>
  )
}
