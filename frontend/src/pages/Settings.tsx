import React from 'react'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Msg, Field, inputCls, Spinner, Skeleton } from '../components/ui'

export default function Settings() {
  const [cfg, setCfg] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')
  const [exp, setExp] = React.useState('60')
  React.useEffect(() => { apiGet('/api/v1/config').then(setCfg).catch((e: any) => setMsg(e.message || String(e))).finally(() => setLoading(false)) }, [])
  const rows = cfg ? Object.entries(cfg).filter(([k]) => k !== 'structure' && k !== 'config_files') : []
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Paramètres</h2>
      <Msg text={msg} />
      {loading ? (
        <div className="card"><Skeleton lines={5} /></div>
      ) : (
        <>
          <Card title="Configuration (secrets caviardés)">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm max-w-2xl">
              {rows.map(([k, v]) => (
                <React.Fragment key={k}>
                  <dt className="text-slate-400 font-mono">{k}</dt>
                  <dd className="font-mono break-all">{String(v)}</dd>
                </React.Fragment>
              ))}
            </dl>
            <div className="flex gap-2 mt-4 items-end">
              <Field label="Durée session JWT (minutes)">
                <input className={inputCls} value={exp} onChange={(e) => setExp(e.target.value)} />
              </Field>
              <button className="btn" onClick={() => apiCall('/api/v1/config', 'PUT', { jwt_expire_min: Number(exp) }).then(setCfg).catch((e: any) => setMsg(e.message))}>Appliquer</button>
            </div>
          </Card>
          <Card title="Structure /etc/infraos">
            <p className="text-sm">Fichiers : <span className="font-mono">{(cfg?.config_files || []).join(', ') || '…'}</span></p>
            <p className="text-sm text-slate-400 mt-1">Dossiers : {(cfg?.structure || []).join(' · ')}</p>
          </Card>
        </>
      )}
    </div>
  )
}