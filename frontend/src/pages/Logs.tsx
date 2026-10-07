import React from 'react'
import { apiGet } from '../lib/api'
import { Card, Badge, Msg, Spinner, Skeleton } from '../components/ui'

export default function Logs() {
  const [events, setEvents] = React.useState<any[]>([])
  const [journal, setJournal] = React.useState('')
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  React.useEffect(() => {
    apiGet<{ events: any[] }>('/api/v1/events?limit=30').then((r) => setEvents(r.events)).catch((e: any) => setMsg(e.message || String(e))).finally(() => setLoading(false))
    apiGet<{ logs: string }>('/api/v1/logs/journal?service=infraos-api&lines=30').then((r) => setJournal(r.logs)).catch(() => {})
  }, [])
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Logs & audit</h2>
      <Msg text={msg} />
      {loading ? <div className="card"><Skeleton lines={5} /></div> : (
      <Card title="Piste d'audit — qui / quoi / où / quand / résultat">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-slate-400 border-b border-slate-800">
                <th className="py-1 pr-2">Heure</th><th className="pr-2">Utilisateur</th><th className="pr-2">Action</th>
                <th className="pr-2">Ressource</th><th className="pr-2">IP</th><th>Résultat</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e: any, i: number) => (
                <tr key={i} className="border-b border-slate-800/50">
                  <td className="py-1 pr-2 font-mono">{String(e.ts).slice(5, 19)}</td>
                  <td className="pr-2"><b>{e.actor}</b></td>
                  <td className="pr-2">{e.type}</td>
                  <td className="pr-2 font-mono">{e.resource || '—'}</td>
                  <td className="pr-2 font-mono">{e.ip || '—'}</td>
                  <td><Badge value={e.result || 'SUCCESS'} good={['SUCCESS']} bad={['FAILURE', 'DENIED']} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {events.length === 0 && <p className="text-sm text-slate-400">Aucun événement.</p>}
      </Card>
      )}
      <Card title="journald — infraos-api (30 lignes)"><pre className="text-xs whitespace-pre-wrap">{journal.slice(-3000) || '…'}</pre></Card>
    </div>
  )
}
