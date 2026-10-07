import React from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../../lib/api'
import { Card, Msg, Spinner, Badge, Stat, Field, inputCls } from '../../components/ui'

export default function IdentityJoin() {
  const [info, setInfo] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  React.useEffect(() => {
    apiGet<any>('/api/v1/identity/domain/join')
      .then(setInfo).catch((e) => setMsg(String(e))).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner label="Chargement des consignes de jointure…" />
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Jointure au domaine</h2>
        <Link className="btn" to="/identity">← Vue d'ensemble</Link>
      </div>
      <Msg text={msg} />
      {info && !info.provisioned && (
        <div className="card border-yellow-700 bg-yellow-900/20 text-sm text-yellow-300">
          {info.detail} — <Link className="underline" to="/identity/domain">créer le domaine</Link>
        </div>
      )}
      {info?.provisioned && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label="Domaine" value={info.domain} />
            <Stat label="NetBIOS" value={info.netbios} />
            <Stat label="Contrôleur" value={info.domain_controller} />
            <Stat label="DNS du domaine" value={info.dns_server} />
          </div>
          <Card title="Windows (10/11, Server)">
            <ol className="list-decimal ml-5 space-y-1 text-sm">
              {(info.windows?.steps || []).map((s: string, i: number) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
            <p className="text-xs text-slate-400 mt-2">
              Compte : {info.admin_user}@{info.domain} — vérifier
              <code className="mx-1">ipconfig /all</code> puis
              <code className="mx-1">gpupdate /force</code>.
            </p>
          </Card>
          <Card title="Linux (Ubuntu 22.04+, Debian 12+, Rocky/Alma 9+)">
            <Field label="Paquets">
              <input className={inputCls} readOnly value={info.linux?.packages || ''} />
            </Field>
            <ol className="list-decimal ml-5 space-y-1 text-sm mt-3">
              {(info.linux?.steps || []).map((s: string, i: number) => (
                <li key={i} className="break-words">{s}</li>
              ))}
            </ol>
            <div className="flex flex-wrap gap-2 mt-3">
              {(info.linux?.distros || []).map((d: string) => (
                <Badge key={d} value={d} good={[d]} />
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
