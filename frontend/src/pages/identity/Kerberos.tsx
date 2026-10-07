import React from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../../lib/api'
import { apiCall } from '../../lib/client'
import { Card, Msg, Field, inputCls, Spinner, Badge, Stat } from '../../components/ui'

export default function IdentityKerberos() {
  const [info, setInfo] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [test, setTest] = React.useState({ username: '', password: '' })
  const [result, setResult] = React.useState<any>(null)
  const [busy, setBusy] = React.useState(false)

  const load = () => apiGet<any>('/api/v1/identity/domain/kerberos')
    .then(setInfo).catch((e) => setMsg(String(e))).finally(() => setLoading(false))
  React.useEffect(() => { load() }, [])

  async function runTest() {
    setBusy(true); setResult(null); setMsg('')
    try { setResult(await apiCall('/api/v1/identity/test/kerberos', 'POST', test)) }
    catch (e: any) { setMsg(e.message || String(e)) }
    finally { setBusy(false) }
  }

  if (loading) return <Spinner label="Chargement Kerberos…" />
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Kerberos</h2>
        <Link className="btn" to="/identity">← Vue d'ensemble</Link>
      </div>
      <Msg text={msg} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Statut" value={info?.status || '—'}
          tone={info?.status === 'healthy' ? 'ok' : info?.status === 'degraded' ? 'warn' : 'bad'} />
        <Stat label="Realm" value={info?.realm || '—'} />
        <Stat label="Keytab" value={info?.keytab ? 'présente' : 'absente'}
          tone={info?.keytab ? 'ok' : 'warn'} />
        <Stat label="Synchro NTP" value={info?.time_sync?.ntp || '—'}
          tone={info?.time_sync?.synchronized ? 'ok' : 'warn'} />
      </div>
      <Card title="Configuration (/etc/krb5.conf)">
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div><dt className="text-xs text-slate-400">KDC</dt>
            <dd>{(info?.kdc || []).join(', ') || '—'}</dd></div>
          <div><dt className="text-xs text-slate-400">Admin server</dt>
            <dd>{(info?.admin_server || []).join(', ') || '—'}</dd></div>
        </dl>
        <p className="text-xs text-slate-400 mt-2">
          Kerberos exige un écart d'horloge &lt; 5 minutes (KRB_AP_ERR_SKEW).
        </p>
      </Card>
      <Card title="Tickets (klist)">
        <pre className="text-xs whitespace-pre-wrap break-all">{info?.tickets || '—'}</pre>
      </Card>
      <Card title="Principaux de la keytab (klist -k)">
        <pre className="text-xs whitespace-pre-wrap break-all">{info?.principals_detail || '—'}</pre>
      </Card>
      <Card title="Tester une authentification (kinit)">
        <div className="flex gap-3 items-end flex-wrap">
          <Field label="Utilisateur">
            <input className={inputCls} value={test.username}
              onChange={(e) => setTest({ ...test, username: e.target.value })} />
          </Field>
          <Field label="Mot de passe (stdin, jamais dans l'URL)">
            <input className={inputCls} type="password" value={test.password}
              onChange={(e) => setTest({ ...test, password: e.target.value })} />
          </Field>
          <button className="btn" disabled={busy || !test.username || !test.password}
            onClick={runTest}>kinit</button>
        </div>
        {result && (
          <div className="mt-3 text-sm">
            <Badge value={result.success ? 'PASS' : 'ERROR'} good={['PASS']} bad={['ERROR']} />
            <span className="ml-2">{result.principal}</span>
            <p className="text-xs mt-1">{result.detail}</p>
          </div>
        )}
      </Card>
    </div>
  )
}
