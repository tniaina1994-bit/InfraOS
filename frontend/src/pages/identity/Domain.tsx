import React from 'react'
import { apiGet } from '../../lib/api'
import { apiCall } from '../../lib/client'
import { Card, Table, Badge, Msg, Field, inputCls, Spinner } from '../../components/ui'

export default function IdentityDomain() {
  const [info, setInfo] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [busy, setBusy] = React.useState(false)
  const [form, setForm] = React.useState({
    domain: 'corp.example.internal', netbios: 'CORP', hostname: '', ip: '',
    admin_password: '', stop_named: true, confirm: false,
  })
  const [preflight, setPreflight] = React.useState<any>(null)
  const [result, setResult] = React.useState<any>(null)

  const load = () => apiGet<any>('/api/v1/identity/domain')
    .then(setInfo).catch((e) => setMsg(String(e))).finally(() => setLoading(false))
  React.useEffect(() => { load() }, [])

  async function check() {
    setBusy(true); setMsg(''); setPreflight(null)
    try {
      const q = new URLSearchParams({
        domain: form.domain, netbios: form.netbios,
        hostname: form.hostname, ip: form.ip,
      })
      setPreflight(await apiGet<any>(`/api/v1/identity/domain/preflight?${q}`))
    } catch (e: any) { setMsg(e.message || String(e)) }
    finally { setBusy(false) }
  }

  async function provision() {
    setBusy(true); setMsg(''); setResult(null)
    try {
      const out = await apiCall('/api/v1/identity/domain/setup', 'POST', form)
      setResult(out)
      if (out.status === 'done') setMsg('Domaine provisionné avec succès')
      else if (out.status === 'planned') setMsg('Prévisualisation — confirmez pour exécuter')
      else setMsg(out.detail || `Statut : ${out.status}`)
      await load()
    } catch (e: any) { setMsg(e.message || String(e)) }
    finally { setBusy(false) }
  }

  async function backup() {
    setBusy(true)
    try {
      const out = await apiCall('/api/v1/identity/domain/backup', 'POST')
      setMsg(`Sauvegarde : ${out.backup} (${out.size} octets)`)
    } catch (e: any) { setMsg(e.message || String(e)) }
    finally { setBusy(false) }
  }

  async function uninstall() {
    if (!confirm('Desinstaller le Domain Controller ? (backup requis, confirm explicite)')) return
    setBusy(true)
    try {
      const out = await apiCall('/api/v1/identity/domain?confirm=true', 'DELETE')
      setMsg(out.detail || out.status || 'Demande enregistrée')
    } catch (e: any) { setMsg(e.message || String(e)) }
    finally { setBusy(false) }
  }

  if (loading) return <Spinner label="Chargement du domaine…" />
  const provisioned = !!info?.provisioned

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Domaine — provision Samba AD DC</h2>
      <Msg text={msg} />

      {provisioned && (
        <>
          <Card title="Domaine actuel"
            right={<Badge value={info.status || 'active'} good={['active', 'provisioning']} />}>
            <dl className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
              {[
                ['Domaine (realm)', info.domain], ['NetBIOS', info.netbios_name],
                ['FQDN DC', info.fqdn || info.hostname], ['IP DC', info.ip],
                ['Administrateur', info.admin_user], ['Créé le', info.provisioned_at],
                ['Créé par', info.created_by], ['DNS backend', ''],
              ].map(([k, v]) => (
                <div key={String(k)}>
                  <dt className="text-xs text-slate-400">{k}</dt>
                  <dd className="break-words">{v || '—'}</dd>
                </div>
              ))}
            </dl>
            <div className="flex gap-2 mt-4 flex-wrap">
              <button className="btn" onClick={backup} disabled={busy}>Sauvegarder (tar)</button>
              <button className="btn bg-red-900 hover:bg-red-800" onClick={uninstall} disabled={busy}>
                Desinstaller…
              </button>
            </div>
          </Card>
          {info.live && (
            <Card title="samba-tool domain info (live)">
              <pre className="text-xs overflow-x-auto">{JSON.stringify(info.live, null, 2)}</pre>
            </Card>
          )}
        </>
      )}

      {!provisioned && (
        <Card title="Créer le domaine (assistant)">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Field label="Domaine (realm DNS)">
              <input className={inputCls} value={form.domain}
                onChange={(e) => setForm({ ...form, domain: e.target.value })}
                placeholder="corp.example.internal" />
            </Field>
            <Field label="NetBIOS">
              <input className={inputCls} value={form.netbios}
                onChange={(e) => setForm({ ...form, netbios: e.target.value })}
                placeholder="CORP" />
            </Field>
            <Field label="Nom d'hôte du DC">
              <input className={inputCls} value={form.hostname}
                onChange={(e) => setForm({ ...form, hostname: e.target.value })}
                placeholder="dc1" />
            </Field>
            <Field label="IP du DC">
              <input className={inputCls} value={form.ip}
                onChange={(e) => setForm({ ...form, ip: e.target.value })}
                placeholder="192.168.1.39" />
            </Field>
            <Field label="Mot de passe Administrator (8+ car.)">
              <input className={inputCls} type="password" value={form.admin_password}
                onChange={(e) => setForm({ ...form, admin_password: e.target.value })} />
            </Field>
            <div className="flex flex-col gap-2 text-sm pt-4">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={form.stop_named}
                  onChange={(e) => setForm({ ...form, stop_named: e.target.checked })} />
                Arrêter le service DNS local (named) — requis, port 53
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={form.confirm}
                  onChange={(e) => setForm({ ...form, confirm: e.target.checked })} />
                Je confirme la création du domaine (irréversible)
              </label>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button className="btn" onClick={check} disabled={busy}>1. Préflight</button>
            <button className="btn" onClick={provision} disabled={busy || !form.confirm}>
              2. Créer le domaine
            </button>
          </div>
        </Card>
      )}

      {preflight && (
        <Card title={`Préflight — ${preflight.ok ? 'OK' : 'attention'}`}
          right={<Badge value={preflight.ok ? 'PASS' : 'WARNING'} good={['PASS']} />}>
          <Table rows={preflight.checks || []} keyOf={(c: any) => c.check}
            columns={[
              ['Contrôle', (c: any) => c.check],
              ['État', (c: any) => <Badge value={c.status} good={['ok']} bad={['error']} />],
              ['Détail', (c: any) => <span className="text-xs">{c.detail}</span>],
            ]} />
        </Card>
      )}

      {result && (
        <Card title={`Résultat — ${result.status}`}>
          <Table rows={result.steps || []} keyOf={(s: any, i: number) => s.step || i}
            columns={[
              ['Étape', (s: any) => s.step],
              ['OK', (s: any) => <Badge value={s.status} good={['ok']} bad={['error']} />],
              ['Détail', (s: any) => <span className="text-xs">{s.detail}</span>],
            ]} />
          {result.detail && <p className="text-sm mt-2">{result.detail}</p>}
        </Card>
      )}
    </div>
  )
}
