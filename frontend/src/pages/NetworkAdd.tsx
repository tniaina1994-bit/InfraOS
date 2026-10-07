import React from 'react'
import { useNavigate } from 'react-router-dom'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Msg, Field, inputCls, Spinner } from '../components/ui'

type AddKind = 'vlan' | 'bridge'

export default function NetworkAdd() {
  const nav = useNavigate()
  const [kind, setKind] = React.useState<AddKind>('vlan')
  const [ifs, setIfs] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [busy, setBusy] = React.useState(false)
  const [msg, setMsg] = React.useState('')
  const [vlan, setVlan] = React.useState({ interface: '', vlan_id: 10, cidr: '', confirm: false })
  const [br, setBr] = React.useState({ name: 'br0', cidr: '', confirm: false })

  React.useEffect(() => {
    apiGet<{ interfaces: any[] }>('/api/v1/network/interfaces')
      .then((r) => {
        const list = r.interfaces || []
        setIfs(list)
        const first = list.find((i: any) => (i.name || '').startsWith('eth') || (i.name || '').startsWith('en'))
        setVlan((v) => ({ ...v, interface: v.interface || first?.name || list[0]?.name || '' }))
      })
      .catch((e: any) => setMsg(e.message || String(e)))
      .finally(() => setLoading(false))
  }, [])

  async function submitVlan() {
    setBusy(true)
    try {
      const r = await apiCall('/api/v1/network/vlan', 'POST', vlan)
      setMsg(r.reload
        ? `VLAN ${r.staged} créé et appliqué (reload rc=${r.reload_rc})`
        : `VLAN ${r.staged} enregistré — cochez « appliquer » pour recharger networkd`)
    } catch (e: any) { setMsg(e.message || String(e)) }
    finally { setBusy(false) }
  }

  async function submitBridge() {
    setBusy(true)
    try {
      const r = await apiCall('/api/v1/network/bridge', 'POST', br)
      setMsg(r.reload
        ? `Bridge ${r.staged} créé et appliqué (reload rc=${r.reload_rc})`
        : `Bridge ${r.staged} enregistré — cochez « appliquer » pour recharger networkd`)
    } catch (e: any) { setMsg(e.message || String(e)) }
    finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-2xl font-bold">Ajouter une interface</h2>
        <button className="btn" onClick={() => nav('/network')}>← Retour au réseau</button>
      </div>
      <Msg text={msg} />
      <div className="flex gap-2">
        <button
          className={`btn ${kind === 'vlan' ? 'bg-blue-600 hover:bg-blue-500' : ''}`}
          onClick={() => setKind('vlan')}
        >VLAN</button>
        <button
          className={`btn ${kind === 'bridge' ? 'bg-blue-600 hover:bg-blue-500' : ''}`}
          onClick={() => setKind('bridge')}
        >Bridge (pont)</button>
      </div>
      {loading && <Spinner label="Chargement des interfaces…" />}
      {!loading && kind === 'vlan' && (
        <Card title="Créer une interface VLAN">
          <div className="space-y-3 max-w-xl">
            <Field label="Interface parente">
              <input
                className={inputCls}
                list="parent-ifaces"
                value={vlan.interface}
                onChange={(e) => setVlan({ ...vlan, interface: e.target.value })}
                placeholder="eth0"
              />
              <datalist id="parent-ifaces">
                {ifs.map((i) => <option key={i.name} value={i.name} />)}
              </datalist>
            </Field>
            <Field label="ID VLAN (1–4094)">
              <input
                className={inputCls}
                type="number"
                min={1}
                max={4094}
                value={vlan.vlan_id}
                onChange={(e) => setVlan({ ...vlan, vlan_id: Number(e.target.value) })}
              />
            </Field>
            <Field label="CIDR (optionnel, ex: 192.168.20.1/24)">
              <input
                className={inputCls}
                value={vlan.cidr}
                onChange={(e) => setVlan({ ...vlan, cidr: e.target.value })}
                placeholder="192.168.20.1/24"
              />
            </Field>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={vlan.confirm}
                onChange={(e) => setVlan({ ...vlan, confirm: e.target.checked })}
              />
              Appliquer immédiatement (networkctl reload)
            </label>
            <p className="text-xs text-slate-400">
              Crée <span className="font-mono">10-infraos-{vlan.interface || 'eth0'}.{vlan.vlan_id}.netdev</span> dans /etc/systemd/network/.
            </p>
            <button className="btn bg-blue-600 hover:bg-blue-500" onClick={submitVlan} disabled={busy || !vlan.interface}>
              {busy ? 'Création…' : 'Créer le VLAN'}
            </button>
          </div>
        </Card>
      )}
      {!loading && kind === 'bridge' && (
        <Card title="Créer un bridge (pont réseau)">
          <div className="space-y-3 max-w-xl">
            <Field label="Nom (ex: br0, br-lan)">
              <input
                className={inputCls}
                value={br.name}
                onChange={(e) => setBr({ ...br, name: e.target.value })}
                placeholder="br0"
              />
            </Field>
            <Field label="CIDR (optionnel, ex: 192.168.1.1/24)">
              <input
                className={inputCls}
                value={br.cidr}
                onChange={(e) => setBr({ ...br, cidr: e.target.value })}
                placeholder="192.168.1.1/24"
              />
            </Field>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={br.confirm}
                onChange={(e) => setBr({ ...br, confirm: e.target.checked })}
              />
              Appliquer immédiatement (networkctl reload)
            </label>
            <p className="text-xs text-slate-400">
              Crée <span className="font-mono">10-infraos-{br.name}.netdev</span> (Kind=bridge) dans /etc/systemd/network/.
            </p>
            <button className="btn bg-blue-600 hover:bg-blue-500" onClick={submitBridge} disabled={busy || !br.name}>
              {busy ? 'Création…' : 'Créer le bridge'}
            </button>
          </div>
        </Card>
      )}
    </div>
  )
}
