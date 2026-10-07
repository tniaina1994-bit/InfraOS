import React from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../../lib/api'
import { apiCall } from '../../lib/client'
import { Card, Table, Badge, Msg, Field, inputCls, Spinner, Empty } from '../../components/ui'

export default function IdentityGroups() {
  const [list, setList] = React.useState<any>({ items: [], count: 0 })
  const [sel, setSel] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [form, setForm] = React.useState({ name: '', description: '' })
  const [mem, setMem] = React.useState({ add: '', remove: '' })

  const load = () => apiGet<any>('/api/v1/identity/groups')
    .then(setList).catch((e) => setMsg(String(e))).finally(() => setLoading(false))
  React.useEffect(() => { load() }, [])

  async function detail(name: string) {
    try { setSel(await apiGet<any>(`/api/v1/identity/groups/${name}`)) }
    catch (e: any) { setMsg(e.message || String(e)) }
  }
  async function act(fn: () => Promise<any>, done: string) {
    try { await fn(); setMsg(done); await load() }
    catch (e: any) { setMsg(e.message || String(e)) }
  }

  if (loading) return <Spinner label="Chargement des groupes AD…" />
  const noDomain = !list.count && !!list.detail

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Groupes du domaine</h2>
        <Link className="btn" to="/identity">← Vue d'ensemble</Link>
      </div>
      <Msg text={msg} />
      {noDomain && (
        <div className="card border-yellow-700 bg-yellow-900/20 text-sm text-yellow-300">
          {list.detail} — <Link className="underline" to="/identity/domain">créer le domaine</Link>
        </div>
      )}
      <Card title={`Groupes (${list.count || 0})`}>
        <Table rows={list.items || []} keyOf={(g: any) => g.name}
          columns={[
            ['Groupe', (g: any) => g.name],
            ['Actions', (g: any) => (
              <div className="flex gap-2">
                <button className="btn" onClick={() => detail(g.name)}>Membres</button>
                <button className="btn" onClick={() => act(
                  () => apiCall(`/api/v1/identity/groups/${g.name}`, 'DELETE'),
                  `${g.name} supprimé`)}>Supprimer</button>
              </div>
            )],
          ]} />
        {!noDomain && !list.count && <Empty text="Aucun groupe personnalisé" />}
      </Card>

      {sel && (
        <Card title={`Membres — ${sel.name} (${sel.member_count ?? (sel.members || []).length})`}
          right={<button className="btn" onClick={() => setSel(null)}>Fermer</button>}>
          <p className="text-sm">{sel.description || '—'}</p>
          <ul className="text-sm mt-2 space-y-1">
            {(sel.members || []).map((m: string) => (
              <li key={m} className="px-2 py-1 rounded bg-slate-800 inline-block mr-2">{m}</li>
            ))}
            {!(sel.members || []).length && <Empty text="Aucun membre" />}
          </ul>
          <div className="flex gap-2 mt-3 items-end flex-wrap">
            <Field label="Ajouter un membre">
              <input className={inputCls} value={mem.add}
                onChange={(e) => setMem({ ...mem, add: e.target.value })} />
            </Field>
            <Field label="Retirer un membre">
              <input className={inputCls} value={mem.remove}
                onChange={(e) => setMem({ ...mem, remove: e.target.value })} />
            </Field>
            <button className="btn" onClick={() => act(async () => {
              await apiCall(`/api/v1/identity/groups/${sel.name}/members`, 'POST', {
                add: mem.add ? [mem.add] : [], remove: mem.remove ? [mem.remove] : [],
              })
              setMem({ add: '', remove: '' })
              await detail(sel.name)
            }, 'Membres mis à jour')}>Appliquer</button>
          </div>
        </Card>
      )}

      <Card title="Créer un groupe">
        <div className="flex gap-3 items-end flex-wrap">
          <Field label="Nom">
            <input className={inputCls} value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label="Description">
            <input className={inputCls} value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </Field>
          <button className="btn" disabled={!form.name} onClick={() => act(async () => {
            await apiCall('/api/v1/identity/groups', 'POST', form)
            setForm({ name: '', description: '' })
          }, 'Groupe créé')}>Créer</button>
        </div>
      </Card>
    </div>
  )
}
