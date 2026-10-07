import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom'
import './index.css'
import Dashboard from './pages/Dashboard'
import System from './pages/System'
import Network from './pages/Network'
import NetworkConfigure from './pages/NetworkConfigure'
import NetworkAdd from './pages/NetworkAdd'
import Users from './pages/Users'
import IdentityOverview from './pages/identity/Overview'
import IdentityDomain from './pages/identity/Domain'
import IdentityUsers from './pages/identity/Users'
import IdentityGroups from './pages/identity/Groups'
import IdentityOus from './pages/identity/Ous'
import IdentityComputers from './pages/identity/Computers'
import IdentityPolicies from './pages/identity/Policies'
import IdentityKerberos from './pages/identity/Kerberos'
import IdentityLdap from './pages/identity/Ldap'
import IdentityDnsHealth from './pages/identity/DnsHealth'
import IdentityHealth from './pages/identity/Health'
import IdentityAudit from './pages/identity/Audit'
import IdentityJoin from './pages/identity/Join'
import Modules from './pages/Modules'
import Login from './pages/Login'
import DNS from './pages/DNS'
import DHCP from './pages/DHCP'
import Firewall from './pages/Firewall'
import VPN from './pages/VPN'
import IPAM from './pages/IPAM'
import Discovery from './pages/Discovery'
import Monitoring from './pages/Monitoring'
import Shares from './pages/Shares'
import Backup from './pages/Backup'
import Security from './pages/Security'
import Settings from './pages/Settings'
import Logs from './pages/Logs'
import Updates from './pages/Updates'
import { apiGet, getToken } from './lib/api'

import {
  LayoutDashboard, Server, Activity, Network as NetworkIcon, Globe,
  DownloadCloud, Shield, KeyRound, Database, Radar, Users as UsersIcon,
  FolderOpen, Archive, ShieldCheck, RefreshCw, ScrollText, Boxes, Settings as SettingsIcon, LogOut,
  Cpu, HardDrive, Wifi, Cloud, Lock, Layers, BookOpen, Wrench,
  Cpu as CpuIcon, HardDrive as HardDriveIcon, Wifi as WifiIcon, Cloud as CloudIcon, Lock as LockIcon, Layers as LayersIcon, BookOpen as BookOpenIcon, Wrench as WrenchIcon,
} from 'lucide-react'

// Entrée menu : route, libellé, section, icône, permission requise, module requis
type NavEntry = { to: string; label: string; section: string; icon: any; perm: string | null; mod: string | null }
// Regroupement fonctionnel (design propre InfraOS) :
// Dashboard / Système / Réseau / Sécurité réseau / Annuaire & partage / Protection / Administration
const NAV: NavEntry[] = [
  { to: '/', label: 'Dashboard', section: 'Dashboard', icon: LayoutDashboard, perm: null, mod: null },
  { to: '/system', label: 'Système', section: 'Système', icon: Server, perm: 'system:read', mod: 'system' },
  { to: '/monitoring', label: 'Monitoring', section: 'Système', icon: Activity, perm: 'dashboard:read', mod: 'monitoring' },
  { to: '/updates', label: 'Mises à jour', section: 'Système', icon: RefreshCw, perm: 'updates:read', mod: 'updates' },
  { to: '/logs', label: 'Logs', section: 'Système', icon: ScrollText, perm: 'logs:read', mod: 'logs' },
  { to: '/network', label: 'Réseau', section: 'Réseau', icon: NetworkIcon, perm: 'network:read', mod: 'network' },
  { to: '/dns', label: 'DNS', section: 'Réseau', icon: Globe, perm: 'dns:read', mod: 'dns' },
  { to: '/dhcp', label: 'DHCP', section: 'Réseau', icon: DownloadCloud, perm: 'dashboard:read', mod: 'dhcp' },
  { to: '/discovery', label: 'Découverte', section: 'Réseau', icon: Radar, perm: 'dashboard:read', mod: 'discovery' },
  { to: '/ipam', label: 'IPAM', section: 'Réseau', icon: Database, perm: 'dashboard:read', mod: 'ipam' },
  { to: '/firewall', label: 'Firewall', section: 'Sécurité réseau', icon: Shield, perm: 'firewall:read', mod: 'firewall' },
  { to: '/vpn', label: 'VPN', section: 'Sécurité réseau', icon: KeyRound, perm: 'dashboard:read', mod: 'vpn' },
  { to: '/security', label: 'Sécurité', section: 'Sécurité réseau', icon: ShieldCheck, perm: 'dashboard:read', mod: 'security' },
  // Identity & Domain Controller (§15 — 13 pages sous /identity)
  { to: '/identity', label: 'Identité (AD)', section: 'Annuaire & partage', icon: Layers, perm: 'identity.read', mod: 'identity' },
  { to: '/identity/domain', label: 'Domaine', section: 'Annuaire & partage', icon: Cloud, perm: 'domain.read', mod: 'identity' },
  { to: '/identity/users', label: 'Utilisateurs AD', section: 'Annuaire & partage', icon: UsersIcon, perm: 'users.read', mod: 'identity' },
  { to: '/identity/groups', label: 'Groupes AD', section: 'Annuaire & partage', icon: Boxes, perm: 'groups.read', mod: 'identity' },
  { to: '/identity/ous', label: 'OU', section: 'Annuaire & partage', icon: FolderOpen, perm: 'ou.read', mod: 'identity' },
  { to: '/identity/computers', label: 'Ordinateurs', section: 'Annuaire & partage', icon: Server, perm: 'computers.read', mod: 'identity' },
  { to: '/identity/policies', label: 'Politiques mdp', section: 'Annuaire & partage', icon: Lock, perm: 'identity.policy.read', mod: 'identity' },
  { to: '/identity/kerberos', label: 'Kerberos', section: 'Annuaire & partage', icon: KeyRound, perm: 'kerberos.read', mod: 'identity' },
  { to: '/identity/ldap', label: 'LDAP', section: 'Annuaire & partage', icon: Database, perm: 'ldap.read', mod: 'identity' },
  { to: '/identity/dns', label: 'DNS domaine', section: 'Annuaire & partage', icon: Globe, perm: 'dns.read', mod: 'identity' },
  { to: '/identity/health', label: 'Health Check', section: 'Annuaire & partage', icon: Activity, perm: 'identity.read', mod: 'identity' },
  { to: '/identity/join', label: 'Jointure', section: 'Annuaire & partage', icon: BookOpen, perm: 'identity.read', mod: 'identity' },
  { to: '/identity/audit', label: 'Audit identity', section: 'Annuaire & partage', icon: ScrollText, perm: 'identity.audit.read', mod: 'identity' },
  { to: '/shares', label: 'Fichiers', section: 'Annuaire & partage', icon: FolderOpen, perm: 'dashboard:read', mod: 'fileshare' },
  { to: '/backup', label: 'Sauvegardes', section: 'Protection', icon: Archive, perm: 'dashboard:read', mod: 'backup' },
  { to: '/users', label: 'Comptes locaux', section: 'Administration', icon: UsersIcon, perm: 'users:read', mod: 'identity' },
  { to: '/modules', label: 'Modules', section: 'Administration', icon: Boxes, perm: 'modules:read', mod: null },
  { to: '/settings', label: 'Paramètres', section: 'Administration', icon: SettingsIcon, perm: 'config:read', mod: null },
]

function useFilteredNav() {
  const [items, setItems] = React.useState<NavEntry[]>([])
  const [loading, setLoading] = React.useState(true)
  React.useEffect(() => {
    if (!getToken()) { setLoading(false); return }
    Promise.all([
      apiGet<{ permissions: string[] }>('/api/v1/users/me/permissions').catch(() => ({ permissions: [] as string[] })),
      apiGet<{ modules: { name: string; enabled?: boolean }[] }>('/api/v1/modules').catch(() => ({ modules: [] })),
    ]).then(([me, mods]) => {
      const perms = new Set(me.permissions || [])
      const enabled = new Set((mods.modules || []).filter(m => m.enabled !== false).map(m => m.name))
      setItems(NAV.filter((e) =>
        (!e.perm || perms.has(e.perm)) && (!e.mod || enabled.has(e.mod))
      ))
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])
  return { items, loading }
}

const SECTION_ICONS: Record<string, any> = {
  'Dashboard': LayoutDashboard,
  'Système': CpuIcon,
  'Réseau': WifiIcon,
  'Sécurité réseau': Shield,
  'Annuaire & partage': UsersIcon,
  'Protection': Archive,
  'Administration': SettingsIcon,
}

function Layout({ children }: { children: React.ReactNode }) {
  const { items, loading } = useFilteredNav()
  const nav = useNavigate()
  function logout() {
    fetch(`${import.meta.env.VITE_API_URL || ''}/api/v1/auth/logout`, {
      method: 'POST', headers: { 'Authorization': `Bearer ${getToken()}` }
    }).finally(() => {
      localStorage.removeItem('infraos_token')
      nav('/login')
    })
  }
  const loc = useLocation()
  const [open, setOpen] = React.useState<Record<string, boolean>>({})
  const sections: [string, NavEntry[]][] = []
  for (const e of items) {
    const last = sections[sections.length - 1]
    if (last && last[0] === e.section) last[1].push(e)
    else sections.push([e.section, [e]])
  }
  const isOpen = (name: string, entries: NavEntry[]) =>
    open[name] ?? entries.some((e) => e.to === loc.pathname || (e.to !== '/' && loc.pathname.startsWith(e.to + '/')))
  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 p-4 bg-slate-900 border-r border-slate-800 sticky top-0 h-screen flex flex-col">
        <h1 className="text-xl font-bold mb-3">🖥️ InfraOS <span className="text-xs font-normal text-slate-400">v0.2</span></h1>
        <nav className="flex-1 overflow-y-auto flex flex-col gap-1 pr-1">
          {loading && (
            <div className="space-y-2 py-1" aria-label="Chargement du menu">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-6 rounded-lg bg-slate-800 animate-pulse" />
              ))}
            </div>
          )}
          {!loading && sections.map(([name, entries]) => (
            <div key={name}>
              <button
                onClick={() => setOpen({ ...open, [name]: !isOpen(name, entries) })}
                className="w-full text-left text-[11px] uppercase tracking-wide text-slate-400 hover:text-slate-200 mt-2 mb-1 flex items-center gap-2"
              >
                {(() => {
                  const Icon = SECTION_ICONS[name];
                  return <Icon size={14} className="shrink-0 text-slate-400" />;
                })()}
                {isOpen(name, entries) ? '▾' : '▸'} {name}
              </button>
              {isOpen(name, entries) && entries.map((e) => (
                <Link
                  key={e.to}
                  to={e.to}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-slate-800 ${(loc.pathname === e.to || (e.to !== '/' && loc.pathname.startsWith(e.to + '/'))) ? 'bg-slate-800 font-semibold' : ''}`}
                >
                  <e.icon size={16} className="shrink-0 text-slate-400" />
                  {e.label}
                </Link>
              ))}
            </div>
          ))}
        </nav>
        <div className="pt-2 mt-2 border-t border-slate-800">
          <button
            onClick={logout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800 hover:bg-red-900 text-left text-slate-200"
          >
            <LogOut size={16} className="shrink-0" />
            Déconnexion
          </button>
          <p className="text-xs text-slate-500 mt-2">Debian 13 • FastAPI • LXC dev → ISO</p>
        </div>
      </aside>
      <main className="flex-1 p-6 min-w-0">{children}</main>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="*"
          element={
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/system" element={<System />} />
                <Route path="/network" element={<Network />} />
                <Route path="/network/configure" element={<NetworkConfigure />} />
                <Route path="/network/add" element={<NetworkAdd />} />
                <Route path="/users" element={<Users />} />
                <Route path="/identity" element={<IdentityOverview />} />
                <Route path="/identity/domain" element={<IdentityDomain />} />
                <Route path="/identity/users" element={<IdentityUsers />} />
                <Route path="/identity/groups" element={<IdentityGroups />} />
                <Route path="/identity/ous" element={<IdentityOus />} />
                <Route path="/identity/computers" element={<IdentityComputers />} />
                <Route path="/identity/policies" element={<IdentityPolicies />} />
                <Route path="/identity/kerberos" element={<IdentityKerberos />} />
                <Route path="/identity/ldap" element={<IdentityLdap />} />
                <Route path="/identity/dns" element={<IdentityDnsHealth />} />
                <Route path="/identity/health" element={<IdentityHealth />} />
                <Route path="/identity/join" element={<IdentityJoin />} />
                <Route path="/identity/audit" element={<IdentityAudit />} />
                <Route path="/dns" element={<DNS />} />
                <Route path="/dhcp" element={<DHCP />} />
                <Route path="/firewall" element={<Firewall />} />
                <Route path="/vpn" element={<VPN />} />
                <Route path="/ipam" element={<IPAM />} />
                <Route path="/discovery" element={<Discovery />} />
                <Route path="/monitoring" element={<Monitoring />} />
                <Route path="/shares" element={<Shares />} />
                <Route path="/backup" element={<Backup />} />
                <Route path="/security" element={<Security />} />
                <Route path="/updates" element={<Updates />} />
                <Route path="/logs" element={<Logs />} />
                <Route path="/modules" element={<Modules />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </Layout>
          }
        />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
