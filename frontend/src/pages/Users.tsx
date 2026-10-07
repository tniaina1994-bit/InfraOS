import React from 'react'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Table, Badge, Msg, Field, inputCls, Spinner } from '../components/ui'

export default function Users() {
  const [users, setUsers] = React.useState<any[]>([])
  const [groups, setGroups] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [nu, setNu] = React.useState({ username: '', password: '', role: 'viewer' })
  const [ng, setNg] = React.useState({ name: '', role: 'viewer' })
  async function load() {
    try {
      setUsers((await apiGet<{ users: any[] }>('/api/v1/users')).users)
      setGroups((await apiGet<{ groups: any[] }>('/api/v1/groups')).groups)
    } catch (e: any) { setMsg(e.message || String(e)) }
    finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])
  async function toggleUser(u: any) {
    if (!confirm(`${u.disabled ? 'Activer' : 'Désactiver'} ${u.username} ?`)) return
    try {
      await apiCall(`/api/v1/users/${u.username}/${u.disabled ? 'enable' : 'disable'}`, 'POST')
      await load()
    } catch (e: any) { setMsg(e.message || String(e)) }
  }
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Identité — utilisateurs & groupes</h2>
      <Msg text={msg} />
      {loading && <Spinner label="Chargement de l'annuaire…" />}
      {!loading && (
      <>
      <Card title="Utilisateurs">
        <Table
          rows={users}
          keyOf={(u) => u.username}
          columns={[
            ['Nom', (u) => u.username],
            ['Rôle', (u) => u.role],
            ['Rôle effectif', (u) => <Badge value={u.effective_role} good={['superadmin', 'admin']} />],
            ['Groupes', (u) => (u.groups || []).join(', ') || '—'],
            ['Source', (u) => u.source],
            ['État', (u) => <Badge value={u.disabled ? 'désactivé' : 'actif'} good={['actif']} bad={['désactivé']} />],
            ['Action', (u) => <button className="btn" onClick={() => toggleUser(u)}>{u.disabled ? 'Activer' : 'Désactiver'}</button>],
          ]}
        />
        <div className="flex gap-2 mt-3 flex-wrap items-end">
          <Field label="Nom"><input className={inputCls} value={nu.username} onChange={(e) => setNu({ ...nu, username: e.target.value })} /></Field>
          <Field label="Mot de passe (12 car. + chiffre)"><input className={inputCls} type="password" value={nu.password} onChange={(e) => setNu({ ...nu, password: e.target.value })} /></Field>
          <Field label="Rôle">
            <select className={inputCls} value={nu.role} onChange={(e) => setNu({ ...nu, role: e.target.value })}>
              <option>viewer</option><option>operator</option><option>admin</option>
            </select>
          </Field>
          <button className="btn" onClick={() => apiCall('/api/v1/users', 'POST', nu).then(() => { setNu({ username: '', password: '', role: 'viewer' }); setMsg('Utilisateur créé'); load() }).catch((e: any) => setMsg(e.message))}>Créer</button>
        </div>
      </Card>
      <Card title="Groupes">
        <Table
          rows={groups}
          keyOf={(g) => g.name}
          columns={[
            ['Nom', (g) => g.name],
            ['Rôle conféré', (g) => g.role],
            ['Membres', (g) => String(g.members)],
          ]}
        />
        <div className="flex gap-2 mt-3 flex-wrap items-end">
          <Field label="Nom du groupe"><input className={inputCls} value={ng.name} onChange={(e) => setNg({ ...ng, name: e.target.value })} /></Field>
          <Field label="Rôle">
            <select className={inputCls} value={ng.role} onChange={(e) => setNg({ ...ng, role: e.target.value })}>
              <option>viewer</option><option>operator</option><option>admin</option>
            </select>
          </Field>
          <button className="btn" onClick={() => apiCall('/api/v1/groups', 'POST', ng).then(() => { setNg({ name: '', role: 'viewer' }); setMsg('Groupe créé'); load() }).catch((e: any) => setMsg(e.message))}>Créer groupe</button>
        </div>
      </Card>
      </>
      )}
    </div>
  )
}
