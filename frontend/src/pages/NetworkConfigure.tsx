import React from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiGet } from '../lib/api'
import { apiCall } from '../lib/client'
import { Card, Msg, Field, inputCls, Badge, Spinner } from '../components/ui'

type Method = 'static' | 'dhcp'

export default function NetworkConfigure() {
  const nav = useNavigate()
  const [params] = useSearchParams()
  const [iface, setIface] = React.useState(params.get('iface') || '')
  const [method, setMethod] = React.useState<Method>('static')
  const [cidr, setCidr] = React.useState('')
  const [gateway, setGateway] = React.useState('')
  const [confirm, setConfirm] = React.useState(false)
  const [staged, setStaged] = React.useState<any>(null)
  const [ifs, setIfs] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [busy, setBusy] = React.useState(false)
  const [msg, setMsg] = React.useState('')

  React.useEffect(() => {
    Promise.all([
      apiGet<{ interfaces: any[] }>('/api/v1/network/interfaces').then((r) => setIfs(r.interfaces || [])),
      iface ? loadStaged(iface) : Promise.resolve(),
    ]).catch((e: any) => setMsg(e.message || String(e)))
      .finally(() => setLoading(false))
  }, [])

  function loadStaged(name: string) {
    if (!name) return Promise.resolve()
    return apiGet<any>(`/api/v1/network/config/${encodeURIComponent(name)}`)
      .then((c) => {
        setStaged(c)
        if (c?.exists) {
          setMethod(c.method === 'dhcp' ? 'dhcp' : 'static')
          setCidr(c.cidr || '')
          setGateway(c.gateway || '')
        }
      })
      .catch(() => setStaged(null))
  }

  const current = ifs.find((i) => i.name === iface)
  const v4 = current ? (current.addresses || [])
    .filter((a: any) => a.family === '2')
    .map((a: any) => `${a.address}/${a.netmask}`).join(', ') : ''

  async function submit() {
    if (!iface) { setMsg('Interface requise'); return }
    if (method === 'static' && !cidr) { setMsg('CIDR requis en mode statique'); return }
    setBusy(true)
    try {
      const r = method === 'dhcp'
        ? await apiCall('/api/v1/network/dhcp', 'POST', { interface: iface, confirm })
        : await apiCall('/api/v1/network/static', 'POST', { interface: iface, cidr, gateway, confirm })
      setMsg(r.reload
        ? `${method === 'dhcp' ? 'DHCP' : 'Statique'} appliqué (${r.staged}) — reload rc=${r.reload_rc}`
        : `Configuration ${method === 'dhcp' ? 'DHCP' : 'statique'} enregistrée (${r.staged}) — cochez « appliquer » pour recharger networkd`)
      loadStaged(iface)
    } catch (e: any) { setMsg(e.message || String(e)) }
    finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-2xl font-bold">Configurer une interface</h2>
        <button className="btn" onClick={() => nav('/network')}>← Retour au réseau</button>
      </div>
      <Msg text={msg} />
      {loading && <Spinner label="Chargement…" />}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card title="Configuration de l'interface">
            <div className="space-y-3">
              <Field label="Interface">
                <input
                  className={inputCls}
                  list="iface-list"
                  value={iface}
                  onChange={(e) => setIface(e.target.value)}
                  onBlur={() => loadStaged(iface)}
                  placeholder="eth0"
                />
                <datalist id="iface-list">
                  {ifs.map((i) => <option key={i.name} value={i.name} />)}
                </datalist>
              </Field>
              <div>
                <span className="text-xs text-slate-400">Méthode</span>
                <div className="flex gap-4 mt-1">
                  <label className="flex items-center gap-2 text-sm text-slate-200">
                    <input
                      type="radio"
                      name="method"
                      checked={method === 'static'}
                      onChange={() => setMethod('static')}
                    />
                    IP statique
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-200">
                    <input
                      type="radio"
                      name="method"
                      checked={method === 'dhcp'}
                      onChange={() => setMethod('dhcp')}
                    />
                    DHCP
                  </label>
                </div>
              </div>
              {method === 'static' ? (
                <div className="space-y-3">
                  <Field label="CIDR (ex: 192.168.1.10/24)">
                    <input
                      className={inputCls}
                      value={cidr}
                      onChange={(e) => setCidr(e.target.value)}
                      placeholder="192.168.1.10/24"
                    />
                  </Field>
                  <Field label="Passerelle (optionnel)">
                    <input
                      className={inputCls}
                      value={gateway}
                      onChange={(e) => setGateway(e.target.value)}
                      placeholder="192.168.1.1"
                    />
                  </Field>
                </div>
              ) : (
                <p className="text-sm text-slate-400">
                  L'adresse sera obtenue par le serveur DHCP du réseau
                  (<span className="font-mono">DHCP=yes</span> dans le fichier stage).
                  CIDR et passerelle sont ignorés en mode DHCP.
                </p>
              )}
              <label className="flex items-center gap-2 text-sm text-slate-300">
                <input
                  type="checkbox"
                  checked={confirm}
                  onChange={(e) => setConfirm(e.target.checked)}
                />
                Appliquer immédiatement (networkctl reload)
              </label>
              <p className="text-xs text-yellow-500">
                Attention : si l'interface porte votre session, un reload peut couper l'accès.
                InfraOS sauvegarde automatiquement l'ancien fichier (suffixe .infraos-bak).
              </p>
              <div className="flex gap-2">
                <button className="btn bg-blue-600 hover:bg-blue-500" onClick={submit} disabled={busy}>
                  {busy ? 'Application…' : 'Enregistrer'}
                </button>
                <button className="btn" onClick={() => nav('/network')}>Annuler</button>
              </div>
            </div>
          </Card>
          <Card title="Interface sélectionnée">
            {current ? (
              <div className="space-y-2 text-sm">
                <p><span className="text-slate-400">Nom :</span> <span className="font-mono font-semibold">{current.name}</span></p>
                <p>
                  <span className="text-slate-400">État :</span>{' '}
                  <Badge value={current.up ? 'up' : 'down'} good={['up']} bad={['down']} />
                </p>
                <p>
                  <span className="text-slate-400">Config InfraOS :</span>{' '}
                  {staged?.exists
                    ? <Badge value={staged.method === 'dhcp' ? 'dhcp' : 'statique'} good={['dhcp', 'statique']} />
                    : <span className="text-xs text-slate-500">aucune (gestion système)</span>}
                </p>
                <p><span className="text-slate-400">IPv4 actuelle :</span> <span className="font-mono">{v4 || '—'}</span></p>
                <p><span className="text-slate-400">Vitesse :</span> {current.speed_mbps ? `${current.speed_mbps} Mb/s` : '—'}</p>
                <div className="pt-2">
                  <button
                    className="btn text-xs"
                    onClick={() => apiCall('/api/v1/network/link', 'POST', { interface: current.name, up: !current.up })
                      .then(() => {
                        setMsg(`${current.name} → ${!current.up ? 'up' : 'down'}`)
                        apiGet<{ interfaces: any[] }>('/api/v1/network/interfaces')
                          .then((r) => setIfs(r.interfaces || []))
                          .catch(() => {})
                      })
                      .catch((e: any) => setMsg(e.message))}
                  >
                    {current.up ? 'Arrêter (down)' : 'Monter (up)'}
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-400">
                {iface ? `Interface « ${iface} » introuvable dans la liste.` : 'Choisissez une interface pour afficher son état.'}
              </p>
            )}
          </Card>
        </div>
      )}
    </div>
  )
}
