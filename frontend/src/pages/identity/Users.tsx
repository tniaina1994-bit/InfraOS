import React from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../../lib/api'
import { apiCall } from '../../lib/client'
import { Card, Table, Badge, Msg, Field, inputCls, Spinner, Empty } from '../../components/ui'

export default function IdentityUsers() {
  const [list, setList] = React.useState<any>({ items: [], count: 0 })
  const [sel, setSel] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [form, setForm] = React.useState({
    username: '', password: '', first_name: '', last_name: '', ou: '',
    must_change_password: true,
  })
  const [pwd, setPwd] = React.useState({ name: '', password: '', must_change: true })

  const load = () => apiGet<any>('/api/v1/identity/users')
    .then(setList).catch((e) => setMsg(String(e))).finally(() => setLoading(false))
  React.useEffect(() => { load() }, [])

  async function detail(name: string) {
    try { setSel(await apiGet<any>(`/api/v1/identity/users/${name}`)) }
    catch (e: any) { setMsg(e.message || String(e)) }
  }
  async function act(fn: () => Promise<any>, done: string) {
    try { await fn(); setMsg(done); await load(); setSel(null) }
    catch (e: any) { setMsg(e.message || String(e)) }
  }

  if (loading) return <Spinner label="Chargement des utilisateurs AD…" />
  const noDomain = !list.count && !!list.detail

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Utilisateurs du domaine</h2>
        <Link className="btn" to="/identity">← Vue d'ensemble</Link>
      </div>
      <Msg text={msg} />
      {noDomain && (
        <div className="card border-yellow-700 bg-yellow-900/20 text-sm text-yellow-300">
          {list.detail} — <Link className="underline" to="/identity/domain">créer le domaine</Link>
        </div>
      )}
      <Card title={`Comptes AD (${list.count || 0})`}>
        <Table
          rows={list.items || []}
          keyOf={(u: any) => u.username}
          columns={[
            ['Utilisateur', (u: any) => u.username],
            ['Action', (u: any) => (
              <div className="flex gap-2">
                <button className="btn" onClick={() => detail(u.username)}>Détails</button>
                <button className="btn" onClick={() =>
                  act(() => apiCall(`/api/v1/identity/users/${u.username}/disable`, 'POST'),
                    `${u.username} désactivé`)}>Désactiver</button>
                <button className="btn" onClick={() =>
                  act(() => apiCall(`/api/v1/identity/users/${u.username}`, 'DELETE'),
                    `${u.username} supprimé`)}>Supprimer</button>
              </div>
            )],
          ]}
        />
        {!noDomain && !list.count && <Empty text="Aucun utilisateur (hors Administrator)" />}
      </Card>

      {sel && (
        <Card title={`Fiche — ${sel.username}`}
          right={<button className="btn" onClick={() => setSel(null)}>Fermer</button>}>
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {[
              ['DN', sel.dn], ['Prénom', sel.first_name], ['Nom', sel.last_name],
              ['Département', sel.department], ['Téléphone', sel.telephone],
              ['Description', sel.description],
              ['Actif', String(sel.enabled)],
              ['Changer mdp à la connexion', String(sel.must_change_password)],
            ].map(([k, v]) => (
              <div key={k}><dt className="text-xs text-slate-400">{k}</dt>
                <dd className="break-words">{v || '—'}</dd></div>
            ))}
          </dl>
          <p className="text-sm mt-2">Groupes : {(sel.groups || []).join(', ') || '—'}</p>
          <div className="flex gap-2 mt-3 flex-wrap">
            <button className="btn" onClick={() =>
              act(() => apiCall(`/api/v1/identity/users/${sel.username}/enable`, 'POST'),
                `${sel.username} activé`)}>Activer</button>
            <button className="btn" onClick={() =>
              act(() => apiCall(`/api/v1/identity/users/${sel.username}/unlock`, 'POST'),
                `${sel.username} déverrouillé`)}>Déverrouiller</button>
            <button className="btn" onClick={() => setPwd({ name: sel.username, password: '', must_change: true })}>
              Réinitialiser le mot de passe
            </button>
          </div>
          {pwd.name === sel.username && (
            <div className="flex gap-2 mt-3 items-end flex-wrap">
              <Field label="Nouveau mot de passe (8+ car.)">
                <input className={inputCls} type="password" value={pwd.password}
                  onChange={(e) => setPwd({ ...pwd, password: e.target.value })} />
              </Field>
              <label className="flex items-center gap-2 text-xs text-slate-400 pb-1">
                <input type="checkbox" checked={pwd.must_change}
                  onChange={(e) => setPwd({ ...pwd, must_change: e.target.checked })} />
                Changement obligatoire
              </label>
              <button className="btn" onClick={() =>
                act(async () => {
                  await apiCall(`/api/v1/identity/users/${pwd.name}/password`, 'POST',
                    { password: pwd.password, must_change: pwd.must_change })
                  setPwd({ name: '', password: '', must_change: true })
                }, 'Mot de passe réinitialisé')}>Appliquer</button>
            </div>
          )}
        </Card>
      )}

      <Card title="Créer un utilisateur du domaine">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Field label="Nom d'utilisateur (sAMAccountName)">
            <input className={inputCls} value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })} />
          </Field>
          <Field label="Mot de passe (8+ car.)">
            <input className={inputCls} type="password" value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </Field>
          <Field label="OU (ex. OU=Users)">
            <input className={inputCls} value={form.ou}
              onChange={(e) => setForm({ ...form, ou: e.target.value })} />
          </Field>
          <Field label="Prénom">
            <input className={inputCls} value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
          </Field>
          <Field label="Nom">
            <input className={inputCls} value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
          </Field>
          <label className="flex items-center gap-2 text-xs text-slate-400 pb-1">
            <input type="checkbox" checked={form.must_change_password}
              onChange={(e) => setForm({ ...form, must_change_password: e.target.checked })} />
            Changement de mot de passe obligatoire
          </label>
        </div>
        <button className="btn mt-3" disabled={!form.username || !form.password}
          onClick={() => act(async () => {
            await apiCall('/api/v1/identity/users', 'POST', form)
            setForm({ ...form, username: '', password: '', first_name: '', last_name: '' })
          }, 'Utilisateur créé')}>Créer</button>
      </Card>
    </div>
  )
}
