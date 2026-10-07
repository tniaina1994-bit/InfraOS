# SPDX-License-Identifier: GPL-3.0-or-later
"""Module Manager — coeur du modular monolith.

Un seul processus (infraos-api), un seul service systemd, une seule DB.
Le manager decouvre les manifests (modules/*/manifest.yaml), ordonne par
dependances (requires, tri topo), lie chaque manifest a son backend
(core/infraos/modules/<nom>.py) et expose le lifecycle :
status / enable / disable / install / action.

Pas de microservices : les modules sont des classes dans le monolithe,
appelees en-process, via exec.run() pour le systeme (allow-list + audit).
"""
from __future__ import annotations
import os
from pathlib import Path
import yaml
from . import module_state
from .audit import audit
from .logging_conf import get_logger
from .module_base import ModuleStatus

log = get_logger("infraos.modules")

# Spec point 7 : le manifeste peut utiliser les cles
#   display_name (alias title), dependencies (alias requires),
#   enabled (defaut d'activation si aucun etat runtime).
# Les deux orthographes sont acceptees et normalisees ici.
REQUIRED_KEYS = {"name", "version", "services", "packages"}


def modules_dir() -> Path:
    env = os.getenv("INFRAOS_MODULES_DIR")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    # backend/app/core/infraos/module_manager.py -> repo/modules,
    # ou /opt/infraos/modules en prod
    for cand in (here.parents[4] / "modules", Path("/opt/infraos/modules")):
        if cand.exists():
            return cand
    return here.parents[4] / "modules"


def discover(base: Path | None = None) -> list[dict]:
    """Lit et valide tous les manifests. Jamais d'exception (erreur par module)."""
    base = base or modules_dir()
    out = []
    if not base.exists():
        return out
    for child in sorted(base.iterdir()):
        if child.name == "README.md" or not child.is_dir():
            continue
        mf = child / "manifest.yaml"
        if not mf.exists():
            continue
        try:
            data = yaml.safe_load(mf.read_text()) or {}
            data.setdefault("name", child.name)
            # aliases spec <-> historique
            if "display_name" in data and "title" not in data:
                data["title"] = data["display_name"]
            data.setdefault("title", data["name"])
            if "display_name" not in data:
                data["display_name"] = data["title"]
            if "dependencies" in data and "requires" not in data:
                data["requires"] = data["dependencies"]
            data.setdefault("requires", [])
            if "dependencies" not in data:
                data["dependencies"] = data["requires"]
            if "enabled" not in data:
                data["enabled"] = True
            missing = REQUIRED_KEYS - set(data.keys())
            if missing:
                data["error"] = f"cles manquantes: {sorted(missing)}"
            data.setdefault("services", [])
            data.setdefault("packages", [])
            data.setdefault("description", "")
            out.append(data)
        except Exception as e:
            out.append({"name": child.name, "error": str(e)})
    return out


def resolve_order(manifests: list[dict]) -> list[str]:
    """Tri topologique sur requires. Leve ValueError si cycle ou dependance manquante."""
    names = {m["name"] for m in manifests if "error" not in m}
    deps = {m["name"]: [r for r in m.get("requires", []) if r] for m in manifests if "error" not in m}
    for n, ds in deps.items():
        for d in ds:
            if d not in names:
                raise ValueError(f"module {n}: dependance inconnue {d}")
    order: list[str] = []
    temp: set[str] = set()
    perm: set[str] = set()

    def visit(n: str, stack: list[str]):
        if n in perm:
            return
        if n in temp:
            raise ValueError(f"cycle de dependances: {' -> '.join(stack + [n])}")
        temp.add(n)
        for d in deps.get(n, []):
            visit(d, stack + [n])
        temp.discard(n)
        perm.add(n)
        order.append(n)

    for n in sorted(deps):
        visit(n, [])
    return order


def _backend(name: str):
    """Lie manifest -> classe backend (monolithe, import paresseux)."""
    from .modules import system as mod_system
    from .modules import identity as mod_identity
    from .modules import dns as mod_dns
    from .modules import network as mod_network
    from .modules import dhcp as mod_dhcp
    from .modules import domain as mod_domain
    from .modules import firewall as mod_firewall
    from .modules import vpn as mod_vpn
    from .modules import ipam as mod_ipam
    from .modules import monitoring as mod_monitoring
    from .modules import fileserver as mod_fileserver
    from .modules import backup as mod_backup
    from .modules import updates as mod_updates
    from .modules import discovery as mod_discovery
    from .modules import security as mod_security
    from .modules import loganalyzer as mod_loganalyzer
    from .modules import virtualization as mod_virt
    from .modules import certificates as mod_certs
    table = {
        "system": mod_system.SystemModule,
        "identity": mod_identity.IdentityModule,
        "users-groups": mod_identity.IdentityModule,  # alias historique
        "dns": mod_dns.DnsModule,
        "network": mod_network.NetworkModule,
        "dhcp": mod_dhcp.DhcpModule,
        "domain": mod_domain.DomainModule,
        "firewall": mod_firewall.FirewallModule,
        "vpn": mod_vpn.VpnModule,
        "ipam": mod_ipam.IpamModule,
        "monitoring": mod_monitoring.MonitoringModule,
        "fileshare": mod_fileserver.FileServerModule,
        "backup": mod_backup.BackupModule,
        "updates": mod_updates.UpdateModule,
        "discovery": mod_discovery.DiscoveryModule,
        "security": mod_security.SecurityModule,
        "loganalyzer": mod_loganalyzer.LogAnalyzerModule,
        "virtualization": mod_virt.VirtModule,
        "certificates": mod_certs.CertModule,
    }
    cls = table.get(name)
    return cls() if cls else None


def _default_enabled(mf: dict) -> bool:
    return bool(mf.get("enabled", True))


def status(name: str, data_dir: str | None = None) -> dict:
    manifests = {m["name"]: m for m in discover()}
    mf = manifests.get(name)
    if not mf:
        raise ValueError(f"module inconnu: {name}")
    be = _backend(name)
    live: ModuleStatus | None = be.status() if be else None
    return {
        "name": name,
        "display_name": mf.get("display_name", mf.get("title", name)),
        "title": mf.get("title", name),
        "description": mf.get("description", ""),
        "version": mf.get("version", "?"),
        "enabled": module_state.is_enabled(name, data_dir, _default_enabled(mf)),
        "installed": live.installed if live else None,
        "running": live.running if live else None,
        "detail": live.detail if live else "backend generique (manifest seul)",
        "services": mf.get("services", []),
        "packages": mf.get("packages", []),
        "dependencies": mf.get("dependencies", []),
        "requires": mf.get("requires", []),
        "managed": be is not None,
    }


def dependencies(name: str, data_dir: str | None = None) -> dict:
    """Verifie les dependances : presence + activation de chaque requis."""
    manifests = {m["name"]: m for m in discover()}
    mf = manifests.get(name)
    if not mf:
        raise ValueError(f"module inconnu: {name}")
    deps = []
    ok = True
    for dep in mf.get("requires", []) or []:
        present = dep in manifests
        en = module_state.is_enabled(dep, data_dir,
                                     _default_enabled(manifests[dep])) if present else False
        if not (present and en):
            ok = False
        deps.append({"name": dep, "present": present, "enabled": en})
    return {"name": name, "satisfied": ok, "dependencies": deps}


def list_all(data_dir: str | None = None) -> list[dict]:
    out = []
    for m in discover():
        if "error" in m:
            out.append(m)
            continue
        try:
            out.append(status(m["name"], data_dir))
        except Exception as e:
            out.append({"name": m["name"], "error": str(e)})
    return out


def enable(name: str, actor: str = "api", data_dir: str | None = None) -> dict:
    manifests = {m["name"]: m for m in discover()}
    if name not in manifests:
        raise ValueError(f"module inconnu: {name}")
    # active d'abord les dependances (ordre topo)
    for dep in manifests[name].get("requires", []):
        module_state.set_enabled(dep, True, data_dir)
    module_state.set_enabled(name, True, data_dir)
    audit(f"module enable {name} actor={actor}")
    return status(name, data_dir)


def disable(name: str, actor: str = "api", data_dir: str | None = None) -> dict:
    manifests = {m["name"]: m for m in discover()}
    if name not in manifests:
        raise ValueError(f"module inconnu: {name}")
    dependents = [m["name"] for m in manifests.values()
                  if name in (m.get("requires") or [])
                  and module_state.is_enabled(m["name"], data_dir,
                                              _default_enabled(m))]
    if dependents:
        raise ValueError(f"{name} requis par: {dependents}")
    module_state.set_enabled(name, False, data_dir)
    audit(f"module disable {name} actor={actor}")
    return status(name, data_dir)


def install(name: str, actor: str = "api", data_dir: str | None = None) -> dict:
    """Installe les paquets Debian du manifest (RBAC admin, audite)."""
    from . import apt as apt_mod
    manifests = {m["name"]: m for m in discover()}
    mf = manifests.get(name)
    if not mf:
        raise ValueError(f"module inconnu: {name}")
    res = apt_mod.install_packages(mf.get("packages", []), caller=f"module.{name}")
    audit(f"module install {name} actor={actor} rc={res['rc']}")
    st = status(name, data_dir)
    st["install"] = res
    return st


def uninstall(name: str, actor: str = "api", data_dir: str | None = None) -> dict:
    """Desinstalle : refuse si des modules actifs en dependent, retire les
    paquets Debian du manifest (RBAC admin, audite), puis desactive."""
    from . import apt as apt_mod
    manifests = {m["name"]: m for m in discover()}
    mf = manifests.get(name)
    if not mf:
        raise ValueError(f"module inconnu: {name}")
    dependents = [m["name"] for m in manifests.values()
                  if name in (m.get("requires") or [])
                  and module_state.is_enabled(m["name"], data_dir,
                                              _default_enabled(m))]
    if dependents:
        raise ValueError(f"{name} requis par: {dependents}")
    # keep_packages : paquets installes au provision/exigences systeme (ex. Samba
    # AD DC) — jamais retires par la desinstallation du module (§29 garde Identity).
    to_remove = [] if mf.get("keep_packages") else mf.get("packages", [])
    res = apt_mod.remove_packages(to_remove, caller=f"module.{name}")
    module_state.set_enabled(name, False, data_dir)
    audit(f"module uninstall {name} actor={actor} rc={res['rc']}")
    st = status(name, data_dir)
    st["uninstall"] = res
    return st
