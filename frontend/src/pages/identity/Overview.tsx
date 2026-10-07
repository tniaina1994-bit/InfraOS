import React from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../../lib/api'
import { Card, Table, Badge, Msg, Spinner, Stat } from '../../components/ui'

const LINKS: [string, string][] = [
  ['/identity/domain', 'Domaine'],
  ['/identity/health', 'Health Check'],
  ['/identity/users', 'Utilisateurs'],
  ['/identity/groups', 'Groupes'],
  ['/identity/ous', 'OU'],
  ['/identity/computers', 'Ordinateurs'],
  ['/identity/policies', 'Politiques'],
  ['/identity/kerberos', 'Kerberos'],
  ['/identity/ldap', 'LDAP'],
  ['/identity/dns', 'DNS Health'],
  ['/identity/join', 'Jointure'],
  ['/identity/audit', 'Audit'],
]

export default function IdentityOverview() {
  const [status, setStatus] = React.useState<any>(null)
  const [health, setHealth] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  React.useEffect(() => {
    Promise.all([
      apiGet<any>('/api/v1/identity/status').catch((e) => ({ error: String(e) })),
      apiGet<any>('/api/v1/identity/health').catch((e) => ({ error: String(e) })),
    ]).then(([s, h]) => { setStatus(s); setHealth(h) })
      .catch((e) => setMsg(String(e)))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner label="Chargement du Domain Controller…" />
  const tone = (v: string) => (['PASS', 'healthy', 'active', 'yes'].includes(v) ? 'ok'
    : ['WARNING', 'degraded', 'unconfigured'].includes(v) ? 'warn'
    : ['ERROR', 'error', 'down'].includes(v) ? 'bad' : undefined)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Identité — Domain Controller</h2>
        <div className="flex gap-2">
          <Link className="btn" to="/identity/health">Health Check</Link>
          <Link className="btn" to="/identity/domain">Domaine</Link>
        </div>
      </div>
      <Msg text={msg} />
      {status && !status.provisioned && (
        <div className="card border-yellow-700 bg-yellow-900/20">
          <p className="text-sm text-yellow-300">
            Aucun domaine AD provisionné. Créez le domaine (Samba AD DC) pour activer
            utilisateurs, groupes, Kerberos, LDAP et DNS de domaine.
          </p>
          <Link className="btn mt-2 inline-block" to="/identity/domain">
            Configurer le domaine →
          </Link>
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Statut" value={status?.status || '—'}
          tone={tone(status?.status) as any} />
        <Stat label="Domaine" value={status?.domain || '—'} />
        <Stat label="DNS" value={status?.dns || '—'} tone={tone(status?.dns) as any} />
        <Stat label="Kerberos" value={status?.kerberos || '—'} tone={tone(status?.kerberos) as any} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="LDAP" value={status?.ldap || '—'} tone={tone(status?.ldap) as any} />
        <Stat label="Samba" value={status?.samba || '—'} tone={tone(status?.samba) as any} />
        <Stat label="SYSVOL" value={status?.sysvol || '—'} tone={tone(status?.sysvol) as any} />
        <Stat label="Nom d'hôte DC" value={status?.hostname || '—'} />
      </div>
      {health && (
        <Card title={`Health Check — ${health.overall || ''}`}
          right={<Badge value={health.overall || '?'} good={['PASS']} bad={['ERROR']} />}>
          <Table
            rows={health.checks || []}
            keyOf={(c: any) => c.check}
            columns={[
              ['Vérification', (c: any) => c.check],
              ['État', (c: any) => <Badge value={c.status} good={['PASS']} bad={['ERROR']} />],
              ['Détail', (c: any) => <span className="text-xs">{c.detail}</span>],
            ]}
          />
        </Card>
      )}
      <Card title="Accès rapide">
        <div className="flex flex-wrap gap-2">
          {LINKS.map(([to, label]) => (
            <Link key={to} to={to}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm">
              {label}
            </Link>
          ))}
        </div>
      </Card>
    </div>
  )
}
