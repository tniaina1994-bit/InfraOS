# SPDX-License-Identifier: GPL-3.0-or-later
"""DHCP Kea — scopes/reservations (DB) -> /etc/kea/kea-dhcp4.conf + check + reload.

Baux : lecture du memfile CSV Kea (lecture seule). Allocation : pool + exclusions.
"""
from __future__ import annotations
import csv
import ipaddress
import json
import re
from pathlib import Path

KEA_CONF = Path("/etc/kea/kea-dhcp4.conf")
KEA_LEASES = Path("/var/lib/kea/kea-leases4.csv")
_MAC = re.compile(r"^[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}$")


def validate_scope(subnet: str, start: str, end: str, gateway: str = "") -> dict:
    try:
        net = ipaddress.ip_network(subnet, strict=False)
    except ValueError:
        raise ValueError(f"subnet invalide: {subnet}")
    if net.version != 4:
        raise ValueError("Kea v1 : IPv4 uniquement")
    try:
        s, e = ipaddress.IPv4Address(start), ipaddress.IPv4Address(end)
    except ValueError:
        raise ValueError("pool_start/end IPv4 invalides")
    if s not in net or e not in net or int(e) <= int(s):
        raise ValueError("pool hors subnet ou inverse")
    if gateway:
        try:
            g = ipaddress.IPv4Address(gateway)
        except ValueError:
            raise ValueError("gateway invalide")
        if g not in net:
            raise ValueError("gateway hors subnet")
    return {"network": str(net), "pool": f"{s}-{e}"}


def validate_reservation(mac: str, ip: str, scope: dict) -> dict:
    if not _MAC.match(mac or ""):
        raise ValueError(f"MAC invalide: {mac}")
    try:
        addr = ipaddress.IPv4Address(ip)
    except ValueError:
        raise ValueError(f"IP invalide: {ip}")
    net = ipaddress.ip_network(scope["subnet"])
    if addr not in net:
        raise ValueError("reservation hors subnet du scope")
    return {"mac": mac.lower(), "ip": str(addr)}


def render_kea(scopes: list[dict]) -> dict:
    subnets = []
    for i, sc in enumerate(scopes, start=1):
        if not sc.get("enabled", True):
            continue
        net = ipaddress.ip_network(sc["subnet"])
        opts = []
        if sc.get("gateway"):
            opts.append({"name": "routers", "data": sc["gateway"]})
        raw_dns = sc.get("dns") or []
        dns = json.loads(raw_dns) if isinstance(raw_dns, str) else list(raw_dns)
        if dns:
            opts.append({"name": "domain-name-servers", "data": ", ".join(dns)})
        if sc.get("domain"):
            opts.append({"name": "domain-name", "data": sc["domain"]})
        res = [{"hw-address": r["mac"], "ip-address": r["ip"],
                **({"hostname": r["hostname"]} if r.get("hostname") else {})}
               for r in sc.get("reservations", [])]
        subnets.append({"id": i, "subnet": str(net),
                        "pools": [{"pool": f"{sc['pool_start']} - {sc['pool_end']}"}],
                        "option-data": opts, "reservations": res,
                        "valid-lifetime": sc.get("lease_valid", 3600),
                        "max-valid-lifetime": sc.get("lease_max", 7200)})
    return {"Dhcp4": {"interfaces-config": {"interfaces": ["*"]},
                      "lease-database": {"type": "memfile",
                                         "persist": True,
                                         "name": str(KEA_LEASES)},
                      "valid-lifetime": 3600, "subnet4": subnets}}


def write_and_check(conf: dict) -> dict:
    from .exec import run
    try:
        KEA_CONF.parent.mkdir(parents=True, exist_ok=True)
        bak = str(KEA_CONF) + ".infraos-bak"
        if KEA_CONF.exists():
            Path(bak).write_bytes(KEA_CONF.read_bytes())
        KEA_CONF.write_text(json.dumps(conf, indent=2))
    except OSError as e:
        return {"ok": False, "detail": f"ecriture impossible: {e}"}
    r = run("kea-dhcp4", "-t", str(KEA_CONF), timeout=30, caller="dhcp.render")
    return {"ok": r.rc == 0, "detail": r.out[-2000:] or ("kea -t OK" if r.rc == 0 else "kea -t KO")}


def reload() -> dict:
    from .exec import run
    r = run("systemctl", "restart", "kea-dhcp4-server", timeout=60, caller="dhcp.reload")
    return {"rc": r.rc, "detail": r.out[-1000:]}


def leases(limit: int = 100) -> dict:
    """Baux actifs depuis le memfile Kea (lecture seule, tolerant)."""
    out = []
    try:
        with open(KEA_LEASES, newline="") as f:
            for row in csv.DictReader(f):
                out.append({"ip": row.get("address"), "mac": row.get("hwaddr"),
                            "hostname": row.get("hostname"), "valid": row.get("valid_lifetime"),
                            "expire": row.get("expire")})
                if len(out) >= limit:
                    break
        return {"leases": out, "count": len(out), "source": str(KEA_LEASES)}
    except FileNotFoundError:
        return {"leases": [], "count": 0, "detail": "memfile absent (serveur jamais demarre ?)"}
    except OSError as e:
        return {"leases": [], "count": 0, "detail": str(e)}
