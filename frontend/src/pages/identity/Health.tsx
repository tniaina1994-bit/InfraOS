import React from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../../lib/api'
import { Card, Table, Badge, Msg, Spinner, Stat } from '../../components/ui'

export default function IdentityHealth() {
  const [health, setHealth] = React.useState<any>(null)
  const [services, setServices] = React.useState<any>(null)
  const [time, setTime] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  React.useEffect(() => {
    Promise.all([
      apiGet<any>('/api/v1/identity/health').catch((e) => ({ error: String(e) })),
      apiGet<any>('/api/v1/identity/domain/services').catch(() => null),
      apiGet<any>('/api/v1/identity/domain/time').catch(() => null),
    ]).then(([h, s, t]) => { setHealth(h); setServices(s); setTime(t) })
      .catch((e) => setMsg(String(e)))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner label="Health Check en cours…" />
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Identity Health Check</h2>
        <Link className="btn" to="/identity">← Vue d'ensemble</Link>
      </div>
      <Msg text={msg} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Résultat global" value={health?.overall || '—'}
          tone={health?.overall === 'PASS' ? 'ok' : health?.overall === 'WARNING' ? 'warn' : 'bad'} />
        <Stat label="Domaine" value={health?.domain || '—'} />
        <Stat label="Hôte" value={health?.hostname || '—'} />
        <Stat label="Heure" value={time?.ntp || '—'}
          tone={time?.synchronized ? 'ok' : 'warn'} />
      </div>
      <Card title="Vérifications (§20)">
        <Table rows={health?.checks || []} keyOf={(c: any) => c.check}
          columns={[
            ['Contrôle', (c: any) => c.check],
            ['État', (c: any) => <Badge value={c.status} good={['PASS']} bad={['ERROR']} />],
            ['Détail', (c: any) => <span className="text-xs break-words">{c.detail}</span>],
          ]} />
      </Card>
      <Card title="Services (§19)">
        <Table rows={services?.services || []} keyOf={(s: any) => s.service}
          columns={[
            ['Service', (s: any) => s.service],
            ['État', (s: any) => <Badge value={s.status}
              good={['active']} bad={['inactive', 'failed']} />],
            ['Au démarrage', (s: any) => s.enabled],
            ['Requis', (s: any) => s.required ? 'oui' : ''],
          ]} />
      </Card>
      <Card title="Temps & fuseau (§18)">
        <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(time, null, 2)}</pre>
      </Card>
    </div>
  )
}
