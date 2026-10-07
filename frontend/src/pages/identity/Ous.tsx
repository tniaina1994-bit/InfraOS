import React from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../../lib/api'
import { apiCall } from '../../lib/client'
import { Card, Table, Badge, Msg, Field, inputCls, Spinner, Empty } from '../../components/ui'

export default function IdentityOus() {
  const [list, setList] = React.useState<any>({ items: [], count: 0 })
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [form, setForm] = React.useState({ name: '', parent: '', description: '' })
  const [del, setDel] = React.useState<{ dn: string; force: boolean } | null>(null)

  const load = () => apiGet<any>('/api/v1/identity/ous')
    .then(setList).catch((e) => setMsg(String(e))).finally(() => setLoading(false))
  React.useEffect(() => { load() }, [])

  async function act(fn: () => Promise<any>, done: string) {
    try { await fn(); setMsg(done); await load() }
    catch (e: any) { setMsg(e.message || String(e)) }
  }

  if (loading) return <Spinner label="Chargement des OU…" />
  const noDomain = !list.count && !!list.detail

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Unités d'organisation (OU)</h2>
        <Link className="btn" to="/identity">← Vue d'ensemble</Link>
      </div>
      <Msg text={msg} />
      {noDomain && (
        <div className="card border-yellow-700 bg-yellow-900/20 text-sm text-yellow-300">
          {list.detail} — <Link className="underline" to="/identity/domain">créer le domaine</Link>
        </div>
      )}
      <Card title={`OU (${list.count || 0})`}>
        <Table rows={list.items || []} keyOf={(o: any) => o.dn}
          columns={[
            ['Nom', (o: any) => o.name],
            ['DN', (o: any) => <span className="text-xs break-all">{o.dn}</span>],
            ['Système', (o: any) => <Badge value={o.system ? 'oui' : 'non'} good={['non']} />],
            ['Actions', (o: any) => (
              <div className="flex gap-2">
                <button className="btn" onClick={() => setDel({ dn: o.dn, force: false })}>
                  Supprimer
                </button>
              </div>
            )],
          ]} />
        {!noDomain && !list.count && <Empty text="Aucune OU" />}
      </Card>

      {del && (
        <Card title={`Supprimer ${del.dn} ?`}>
          <p className="text-sm text-yellow-300">
            La suppression est irréversible. Si l'OU contient des objets,
            cochez « forcer » (objets déplacés/supprimés selon AD).
          </p>
          <div className="flex gap-3 items-center mt-2">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={del.force}
                onChange={(e) => setDel({ ...del, force: e.target.checked })} />
              Forcer (OU non vide)
            </label>
            <button className="btn" onClick={() => setDel(null)}>Annuler</button>
            <button className="btn bg-red-900 hover:bg-red-800" onClick={() =>
              act(async () => {
                await apiCall(
                  `/api/v1/identity/ous?dn=${encodeURIComponent(del.dn)}&confirm=true&force=${del.force}`,
                  'DELETE')
                setDel(null)
              }, 'OU supprimée')}>Confirmer</button>
          </div>
        </Card>
      )}

      <Card title="Créer une OU">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Field label="Nom (ex. Utilisateurs)">
            <input className={inputCls} value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label="Parent (DN, vide = racine du domaine)">
            <input className={inputCls} value={form.parent}
              onChange={(e) => setForm({ ...form, parent: e.target.value })}
              placeholder="OU=Users" />
          </Field>
          <Field label="Description">
            <input className={inputCls} value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </Field>
        </div>
        <button className="btn mt-3" disabled={!form.name} onClick={() => act(async () => {
          await apiCall('/api/v1/identity/ous', 'POST', form)
          setForm({ name: '', parent: '', description: '' })
        }, 'OU créée')}>Créer</button>
      </Card>
    </div>
  )
}
