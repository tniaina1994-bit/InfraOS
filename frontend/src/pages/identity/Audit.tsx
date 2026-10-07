import React from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../../lib/api'
import { Card, Table, Badge, Msg, Spinner, Empty } from '../../components/ui'

export default function IdentityAudit() {
  const [events, setEvents] = React.useState<any>({ events: [], count: 0 })
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [limit, setLimit] = React.useState(100)
  const load = (n: number) => {
    setLoading(true)
    apiGet<any>(`/api/v1/identity/audit?limit=${n}`)
      .then(setEvents).catch((e) => setMsg(String(e))).finally(() => setLoading(false))
  }
  React.useEffect(() => { load(limit) }, [limit])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Audit — actions Identity</h2>
        <div className="flex gap-2 items-center">
          <select className="input" value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}>
            {[50, 100, 200, 500].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          <button className="btn" onClick={() => load(limit)}>Rafraîchir</button>
          <Link className="btn" to="/identity">← Vue d'ensemble</Link>
        </div>
      </div>
      <Msg text={msg} />
      {loading && <Spinner label="Chargement de l'audit…" />}
      {!loading && (
        <Card title={`Événements identity.* (${events.count || 0})`}>
          <Table rows={events.events || []} keyOf={(e: any, i: number) => `${e.ts}-${i}`}
            columns={[
              ['Horodatage', (e: any) => <span className="text-xs">{e.ts}</span>],
              ['Acteur', (e: any) => e.actor],
              ['Action', (e: any) => e.action],
              ['Ressource', (e: any) => <span className="text-xs break-all">{e.resource}</span>],
              ['Détail', (e: any) => <span className="text-xs break-words">{e.detail}</span>],
              ['Résultat', (e: any) => <Badge value={e.result}
                good={['SUCCESS']} bad={['FAILURE', 'DENIED']} />],
            ]} />
          {!(events.events || []).length && <Empty text="Aucune action identity enregistrée" />}
        </Card>
      )}
    </div>
  )
}
