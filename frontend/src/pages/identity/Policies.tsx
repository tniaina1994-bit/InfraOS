import React from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../../lib/api'
import { apiCall } from '../../lib/client'
import { Card, Table, Msg, Field, inputCls, Spinner } from '../../components/ui'

const FIELDS: [string, string, string][] = [
  ['min_pwd_length', 'Longueur min. (0-128)', 'number'],
  ['history_length', 'Historique (0-24)', 'number'],
  ['min_pwd_age', 'Âge min. jours (0-998)', 'number'],
  ['max_pwd_age', 'Âge max. jours (0-999)', 'number'],
  ['account_lockout_threshold', 'Verrouillage après tentatives (0-999)', 'number'],
  ['account_lockout_duration', 'Durée verrouillage min (0-99999)', 'number'],
  ['reset_account_lockout_after', 'Reset verrouillage min (0-99999)', 'number'],
]

export default function IdentityPolicies() {
  const [policy, setPolicy] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [form, setForm] = React.useState<Record<string, string>>({})

  const load = () => apiGet<any>('/api/v1/identity/policies')
    .then((p) => {
      setPolicy(p)
      const init: Record<string, string> = { complexity: '', store_plaintext: '' }
      for (const [k] of FIELDS) init[k] = String((p.settings || {})[k] ?? '')
      setForm(init)
    }).catch((e) => setMsg(String(e))).finally(() => setLoading(false))
  React.useEffect(() => { load() }, [])

  async function apply() {
    const body: Record<string, any> = {}
    if (form.complexity) body.complexity = form.complexity
    if (form.store_plaintext) body.store_plaintext = form.store_plaintext
    for (const [k] of FIELDS) {
      if (form[k] !== '' && form[k] != null) body[k] = Number(form[k])
    }
    if (!Object.keys(body).length) { setMsg('Aucun changement'); return }
    try {
      await apiCall('/api/v1/identity/policies', 'PUT', body)
      setMsg('Politique appliquée (Samba AD)')
      await load()
    } catch (e: any) { setMsg(e.message || String(e)) }
  }

  if (loading) return <Spinner label="Chargement de la politique…" />
  const settings = policy?.settings || {}

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Politique de mots de passe</h2>
        <Link className="btn" to="/identity">← Vue d'ensemble</Link>
      </div>
      <Msg text={msg} />
      {!policy?.settings || !Object.keys(settings).length ? (
        <div className="card border-yellow-700 bg-yellow-900/20 text-sm text-yellow-300">
          {policy?.detail || 'Politique indisponible'} — la politique AD s'applique
          après création du domaine.
        </div>
      ) : (
        <Card title="Politique actuelle (samba-tool domain passwordsettings)">
          <Table rows={Object.entries(settings).map(([k, v]) => ({ k, v }))}
            keyOf={(r) => r.k}
            columns={[
              ['Paramètre', (r) => r.k],
              ['Valeur', (r) => String(r.v)],
            ]} />
        </Card>
      )}
      <Card title="Modifier">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Field label="Complexité">
            <select className={inputCls} value={form.complexity || ''}
              onChange={(e) => setForm({ ...form, complexity: e.target.value })}>
              <option value="">— inchangé —</option>
              <option value="yes">yes</option>
              <option value="no">no</option>
            </select>
          </Field>
          <Field label="Plaintext stocké">
            <select className={inputCls} value={form.store_plaintext || ''}
              onChange={(e) => setForm({ ...form, store_plaintext: e.target.value })}>
              <option value="">— inchangé —</option>
              <option value="yes">yes</option>
              <option value="no">no</option>
            </select>
          </Field>
          {FIELDS.map(([k, label]) => (
            <Field key={k} label={label}>
              <input className={inputCls} type="number" value={form[k] ?? ''}
                onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
            </Field>
          ))}
        </div>
        <button className="btn mt-3" onClick={apply}>Appliquer (admin)</button>
      </Card>
    </div>
  )
}
