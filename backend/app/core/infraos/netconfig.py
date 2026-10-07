# SPDX-License-Identifier: GPL-3.0-or-later
"""Reseau — lecture via `ip` (toujours), ecriture via systemd-networkd stagee.

Strategie documentee (docs/NETWORK.md) :
- lecture : `ip addr/route/link` (exec allow-list), DNS via /etc/resolv.conf ;
- persistance : drop-ins /etc/systemd/network/10-infraos-*.{network,netdev} ;
- application : `networkctl reload` (faible risque) ; `reconfigure` JAMAIS
  depuis le Web sans confirm explicite ; l'interface portant la session
  courante est protege (refus sans confirm:true + backup auto).
"""
from __future__ import annotations
import ipaddress
import re
from pathlib import Path
from .exec import run

NETDIR = Path("/etc/systemd/network")
_IF = re.compile(r"^[A-Za-z0-9@:_.-]+$")
_PROTECT_HINT = "interface protegee (session courante ?) — confirm:true requis"


def interfaces() -> list[dict]:
    from . import system as sysinfo
    return sysinfo.net_interfaces()


def routes() -> list[dict]:
    r = run("ip", "route", "show", caller="net.routes")
    out = []
    for line in r.out.splitlines():
        line = line.strip()
        if line:
            out.append({"raw": line, "default": line.startswith("default")})
    return out


def dns_resolver() -> dict:
    servers, search = [], []
    try:
        for line in Path("/etc/resolv.conf").read_text().splitlines():
            p = line.split()
            if len(p) >= 2 and p[0] == "nameserver":
                servers.append(p[1])
            elif len(p) >= 2 and p[0] == "search":
                search = p[1:]
    except OSError as e:
        return {"servers": [], "search": [], "detail": str(e)}
    return {"servers": servers, "search": search}


def gateways() -> list[str]:
    return [l["raw"].split("via ")[1].split()[0] for l in routes()
            if l["default"] and "via " in l["raw"]]


def _validate_iface(name: str) -> str:
    if not _IF.match(name or "") or len(name) > 32:
        raise ValueError(f"interface invalide: {name}")
    return name


def static_address(iface: str, cidr: str, gateway: str = "",
                   confirm: bool = False, current_iface: str = "") -> dict:
    """Stage une IP statique (fichier .network). Apply = networkctl reload."""
    _validate_iface(iface)
    try:
        ipaddress.ip_interface(cidr)
    except ValueError:
        raise ValueError(f"CIDR invalide: {cidr}")
    if gateway:
        try:
            ipaddress.ip_address(gateway)
        except ValueError:
            raise ValueError("gateway invalide")
    protected = current_iface and iface == current_iface
    if protected and not confirm:
        raise ValueError(_PROTECT_HINT)
    NETDIR.mkdir(parents=True, exist_ok=True)
    path = NETDIR / f"10-infraos-{iface}.network"
    if path.exists():
        (str(path) + ".infraos-bak").encode()  # noop garde
        Path(str(path) + ".infraos-bak").write_bytes(path.read_bytes())
    cfg = (f"[Match]\nName={iface}\n\n[Network]\nAddress={cidr}\n"
           + (f"Gateway={gateway}\n" if gateway else ""))
    path.write_text(cfg)
    out = {"staged": str(path), "confirm": bool(confirm or not protected)}
    if confirm:
        r = run("networkctl", "reload", timeout=30, caller="net.apply")
        out.update({"reload_rc": r.rc, "reload": r.out[-500:]})
    return out


def _stage_and_maybe_reload(path: Path, cfg: str, iface: str,
                            confirm: bool, protected: bool, method: str) -> dict:
    """Ecrit le fichier .network (backup si existant), reload si confirm."""
    NETDIR.mkdir(parents=True, exist_ok=True)
    if path.exists():
        Path(str(path) + ".infraos-bak").write_bytes(path.read_bytes())
    path.write_text(cfg)
    out = {"staged": str(path), "method": method,
           "confirm": bool(confirm or not protected)}
    if confirm:
        r = run("networkctl", "reload", timeout=30, caller="net.apply")
        out.update({"reload_rc": r.rc, "reload": r.out[-500:]})
    return out


def dhcp_address(iface: str, confirm: bool = False, current_iface: str = "") -> dict:
    """Stage DHCP (DHCP=yes) via systemd-networkd — meme garde-fous que statique."""
    _validate_iface(iface)
    protected = bool(current_iface and iface == current_iface)
    if protected and not confirm:
        raise ValueError(_PROTECT_HINT)
    path = NETDIR / f"10-infraos-{iface}.network"
    cfg = f"[Match]\nName={iface}\n\n[Network]\nDHCP=yes\n"
    return _stage_and_maybe_reload(path, cfg, iface, confirm, protected, "dhcp")


def staged_config(iface: str) -> dict:
    """Retourne la config stagee InfraOS pour une interface (prefill UI)."""
    _validate_iface(iface)
    path = NETDIR / f"10-infraos-{iface}.network"
    if not path.exists():
        return {"interface": iface, "exists": False, "method": None,
                "cidr": "", "gateway": ""}
    text = path.read_text()
    method = "dhcp" if any(l.startswith("DHCP=") for l in text.splitlines()) else "static"
    cidr = gateway = ""
    for line in text.splitlines():
        if line.startswith("Address="):
            cidr = line.split("=", 1)[1].strip()
        elif line.startswith("Gateway="):
            gateway = line.split("=", 1)[1].strip()
    return {"interface": iface, "exists": True, "method": method,
            "cidr": cidr, "gateway": gateway, "file": str(path)}


def vlan(iface: str, vlan_id: int, cidr: str = "", confirm: bool = False) -> dict:
    _validate_iface(iface)
    if not 1 <= int(vlan_id) <= 4094:
        raise ValueError("VLAN 1..4094")
    name = f"{iface}.{vlan_id}"
    NETDIR.mkdir(parents=True, exist_ok=True)
    (NETDIR / f"10-infraos-{name}.netdev").write_text(
        f"[NetDev]\nName={name}\nKind=vlan\n\n[VLAN]\nId={vlan_id}\n")
    if cidr:
        try:
            ipaddress.ip_interface(cidr)
        except ValueError:
            raise ValueError("CIDR invalide")
        (NETDIR / f"10-infraos-{name}.network").write_text(
            f"[Match]\nName={name}\n\n[Network]\nAddress={cidr}\n")
    out = {"staged": name, "confirm": confirm}
    if confirm:
        r = run("networkctl", "reload", timeout=30, caller="net.apply")
        out.update({"reload_rc": r.rc})
    return out


def bridge(name: str, cidr: str = "", confirm: bool = False) -> dict:
    """Cree un pont reseau (netdev Kind=bridge), stage puis reload optionnel."""
    _validate_iface(name)
    if "." in name:
        raise ValueError("nom de bridge sans point (ex: br-lan, br0)")
    NETDIR.mkdir(parents=True, exist_ok=True)
    (NETDIR / f"10-infraos-{name}.netdev").write_text(
        f"[NetDev]\nName={name}\nKind=bridge\n")
    if cidr:
        try:
            ipaddress.ip_interface(cidr)
        except ValueError:
            raise ValueError("CIDR invalide")
        (NETDIR / f"10-infraos-{name}.network").write_text(
            f"[Match]\nName={name}\n\n[Network]\nAddress={cidr}\n")
    out = {"staged": name, "confirm": bool(confirm)}
    if confirm:
        r = run("networkctl", "reload", timeout=30, caller="net.bridge")
        out.update({"reload_rc": r.rc})
    return out


def link_set(iface: str, up: bool) -> dict:
    """Monte/une interface via `ip link set dev <iface> <up|down>` (allow-list)."""
    _validate_iface(iface)
    r = run("ip", "link", "set", "dev", iface, "up" if up else "down",
            timeout=15, caller="net.link")
    if r.rc != 0:
        raise ValueError(f"ip link set a echoue (rc={r.rc}): {r.out[-300:]}")
    return {"interface": iface, "up": up, "detail": r.out[-300:]}


def remove_config(name: str, confirm: bool = False, apply: bool = False) -> dict:
    """Supprime UNIQUEMENT les fichiers stagees InfraOS (10-infraos-<name>.*).
    Utilisable pour une IP statique, un VLAN ou un bridge cree via l'UI."""
    _validate_iface(name)
    if not confirm:
        raise ValueError("confirm:true requis pour supprimer la configuration")
    removed = []
    for suffix in (".network", ".netdev"):
        p = NETDIR / f"10-infraos-{name}{suffix}"
        if p.exists():
            p.unlink()
            removed.append(str(p))
    if not removed:
        raise ValueError(f"aucune configuration InfraOS pour {name}")
    out = {"removed": removed}
    if apply:
        r = run("networkctl", "reload", timeout=30, caller="net.remove")
        out.update({"reload_rc": r.rc})
    return out
