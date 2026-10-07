import React from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../../lib/api'
import { Card, Table, Msg, Spinner, Stat, Badge } from '../../components/ui'

export default function IdentityLdap() {
  const [info, setInfo] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  React.useEffect(() => {
    apiGet<any>('/api/v1/identity/domain/ldap')
      .then(setInfo).catch((e) => setMsg(String(e))).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner label="Chargement LDAP…" />
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">LDAP</h2>
        <Link className="btn" to="/identity">← Vue d'ensemble</Link>
      </div>
      <Msg text={msg} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Statut" value={info?.status || '—'}
          tone={info?.status === 'healthy' ? 'ok' : info?.status === 'degraded' ? 'warn' : 'bad'} />
        <Stat label="Serveur" value={info?.server || '—'} />
        <Stat label="Base DN" value={info?.base_dn || '—'} />
        <Stat label="Annuaire" value={info?.provisioned ? 'AD provisionné' : 'non provisionné'} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="LDAP (389)" value={info?.ldap ? 'joignable' : 'fermé'}
          tone={info?.ldap ? 'ok' : 'bad'} />
        <Stat label="LDAPS (636)" value={info?.ldaps ? 'joignable' : 'fermé'}
          tone={info?.ldaps ? 'ok' : 'warn'} />
        <Stat label="Test de recherche" value={info?.search_test?.ok ? 'OK' : 'échec'}
          tone={info?.search_test?.ok ? 'ok' : 'bad'} />
        <Stat label="Port" value={String(info?.port ?? '—')} />
      </div>
      <Card title="Certificats TLS">
        <Table rows={info?.certificates || []} keyOf={(c: any) => c.path}
          columns={[
            ['Fichier', (c: any) => <span className="text-xs break-all">{c.path}</span>],
            ['Présent', (c: any) => <Badge value={c.exists ? 'oui' : 'non'}
              good={['oui']} bad={['non']} />],
          ]} />
      </Card>
      <Card title="Test de recherche LDAP">
        <pre className="text-xs whitespace-pre-wrap">{info?.search_test?.detail || '—'}</pre>
      </Card>
    </div>
  )
}
