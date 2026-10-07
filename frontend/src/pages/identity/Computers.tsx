import React from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../../lib/api'
import { apiCall } from '../../lib/client'
import { Card, Table, Badge, Msg, Field, inputCls, Spinner, Empty } from '../../components/ui'

export default function IdentityComputers() {
  const [list, setList] = React.useState<any>({ items: [], count: 0 })
  const [sel, setSel] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [form, setForm] = React.useState({ name: '', ou: '', description: '' })

  const load = () => apiGet<any>('/api/v1/identity/computers')
    .then(setList).catch((e) => setMsg(String(e))).finally(() => setLoading(false))
  React.useEffect(() => { load() }, [])

  async function detail(name: string) {
    try { setSel(await apiGet<any>(`/api/v1/identity/computers/${name}`)) }
    catch (e: any) { setMsg(e.message || String(e)) }
  }
  async function act(fn: () => Promise<any>, done: string) {
    try { await fn(); setMsg(done); await load() }
    catch (e: any) { setMsg(e.message || String(e)) }
  }

  if (loading) return <Spinner label="Chargement des ordinateurs AD…" />
  const noDomain = !list.count && !!list.detail

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Ordinateurs du domaine</h2>
        <Link className="btn" to="/identity">← Vue d'ensemble</Link>
      </div>
      <Msg text={msg} />
      {noDomain && (
        <div className="card border-yellow-700 bg-yellow-900/20 text-sm text-yellow-300">
          {list.detail} — <Link className="underline" to="/identity/domain">créer le domaine</Link>
        </div>
      )}
      <Card title={`Comptes machine (${list.count || 0})`}>
        <Table rows={list.items || []} keyOf={(c: any) => c.name}
          columns={[
            ['Ordinateur', (c: any) => c.name],
            ['Actions', (c: any) => (
              <div className="flex gap-2">
                <button className="btn" onClick={() => detail(c.name)}>Détails</button>
                <button className="btn" onClick={() => act(
                  () => apiCall(`/api/v1/identity/computers/${c.name}/disable`, 'POST'),
                  `${c.name} désactivé`)}>Désactiver</button>
                <button className="btn" onClick={() => act(
                  () => apiCall(`/api/v1/identity/computers/${c.name}`, 'DELETE'),
                  `${c.name} supprimé`)}>Supprimer</button>
              </div>
            )],
          ]} />
        {!noDomain && !list.count && <Empty text="Aucun ordinateur enregistré" />}
      </Card>

      {sel && (
        <Card title={`Fiche — ${sel.name}`}
          right={<button className="btn" onClick={() => setSel(null)}>Fermer</button>}>
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {[
              ['DN', sel.dn], ['OS', sel.os], ['Description', sel.description],
              ['Actif', String(sel.enabled)],
            ].map(([k, v]) => (
              <div key={k}><dt className="text-xs text-slate-400">{k}</dt>
                <dd className="break-words">{v || '—'}</dd></div>
            ))}
          </dl>
          <button className="btn mt-3" onClick={() => act(
            () => apiCall(`/api/v1/identity/computers/${sel.name}/enable`, 'POST'),
            `${sel.name} activé`)}>Activer</button>
        </Card>
      )}

      <Card title="Pré-enregistrer un ordinateur">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Field label="Nom (ex. WS-PC01)">
            <input className={inputCls} value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label="OU (ex. OU=Computers)">
            <input className={inputCls} value={form.ou}
              onChange={(e) => setForm({ ...form, ou: e.target.value })} />
          </Field>
          <Field label="Description">
            <input className={inputCls} value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </Field>
        </div>
        <button className="btn mt-3" disabled={!form.name} onClick={() => act(async () => {
          await apiCall('/api/v1/identity/computers', 'POST', form)
          setForm({ name: '', ou: '', description: '' })
        }, 'Compte machine créé')}>Créer</button>
        <p className="text-xs text-slate-400 mt-2">
          La jointure Windows/Linux reste possible sans pré-enregistrement
          (voir <Link className="underline" to="/identity/join">Jointure</Link>).
        </p>
      </Card>
    </div>
  )
}
