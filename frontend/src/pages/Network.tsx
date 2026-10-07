import React from 'react'
import { useNavigate } from 'react-router-dom'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Table, Badge, Msg, Field, inputCls, Spinner } from '../components/ui'

export default function Network() {
  const nav = useNavigate()
  const [ifs, setIfs] = React.useState<any[]>([])
  const [routes, setRoutes] = React.useState<any[]>([])
  const [gateways, setGateways] = React.useState<string[]>([])
  const [dns, setDns] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [msg, setMsg] = React.useState('')

  async function load() {
    try {
      setIfs((await apiGet<{ interfaces: any[] }>('/api/v1/network/interfaces')).interfaces)
      const r = await apiGet<{ routes: any[]; gateways: string[] }>('/api/v1/network/routes')
      setRoutes(r.routes)
      setGateways(r.gateways)
      setDns(await apiGet('/api/v1/network/dns-resolver'))
    } catch (e: any) { setMsg(e.message || String(e)) }
    finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])

  async function toggleLink(i: any) {
    try {
      await apiCall('/api/v1/network/link', 'POST', { interface: i.name, up: !i.up })
      setMsg(`${i.name} → ${!i.up ? 'up' : 'down'}`)
      load()
    } catch (e: any) { setMsg(e.message || String(e)) }
  }

  async function removeConfig(i: any) {
    if (!confirm(`Supprimer la configuration InfraOS de ${i.name} ? (uniquement les fichiers 10-infraos-*)`)) return
    try {
      const r = await apiCall(`/api/v1/network/interface/${encodeURIComponent(i.name)}?confirm=true`, 'DELETE')
      setMsg(`Configuration supprimée : ${(r.removed || []).join(', ')}`)
      load()
    } catch (e: any) { setMsg(e.message || String(e)) }
  }

  const v4 = (i: any) => (i.addresses || [])
    .filter((a: any) => a.family === '2')
    .map((a: any) => `${a.address}/${a.netmask}`).join(', ')

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-2xl font-bold">Réseau</h2>
        <div className="flex gap-2">
          <button className="btn bg-blue-600 hover:bg-blue-500" onClick={() => nav('/network/add')}>
            Ajouter une interface
          </button>
          <button className="btn" onClick={() => nav('/network/configure')}>
            Configurer une interface
          </button>
        </div>
      </div>
      <Msg text={msg} />
      {loading && <Spinner label="Chargement du réseau…" />}
      {!loading && (
        <div className="space-y-4">
          <Card title="Interfaces">
            <Table
              rows={ifs}
              keyOf={(i) => i.name}
              columns={[
                ['Nom', (i) => <span className="font-mono font-semibold">{i.name}</span>],
                ['État', (i) => <Badge value={i.up ? 'up' : 'down'} good={['up']} bad={['down']} />],
                ['IPv4', (i) => <span className="font-mono text-xs">{v4(i) || '—'}</span>],
                ['Vitesse', (i) => i.speed_mbps ? `${i.speed_mbps} Mb/s` : '—'],
                ['Actions', (i) => (
                  <div className="flex gap-1 flex-wrap">
                    <button
                      className="btn text-xs"
                      onClick={() => nav(`/network/configure?iface=${encodeURIComponent(i.name)}`)}
                    >Configurer</button>
                    <button className="btn text-xs" onClick={() => toggleLink(i)}>
                      {i.up ? 'Arrêter' : 'Monter'}
                    </button>
                    <button className="btn text-xs text-red-400 hover:bg-red-900" onClick={() => removeConfig(i)}>
                      Supprimer
                    </button>
                  </div>
                )],
              ]}
            />
          </Card>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card title="Routes">
              {routes.map((r, i) => (
                <div key={i} className="text-sm py-0.5">
                  {r.default && <Badge value="défaut" good={['défaut']} />} <span className="font-mono">{r.raw}</span>
                </div>
              ))}
              <p className="text-sm mt-2 text-slate-400">Passerelles : {gateways.join(', ') || '—'}</p>
            </Card>
            <Card title="DNS résolveur">
              <p className="text-sm">Serveurs : {(dns?.servers || []).join(', ') || '—'}</p>
              <p className="text-sm text-slate-400">Recherche : {(dns?.search || []).join(', ') || '—'}</p>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
