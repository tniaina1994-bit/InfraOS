# SPDX-License-Identifier: GPL-3.0-or-later
"""Moteur BIND9 — rendu zones/options, validation named-checkconf, reload rndc.

Fichiers geres (jamais edites a la main) :
  /etc/bind/infraos/named.conf.infraos  (zones + options, include depuis named.conf)
  /etc/bind/infraos/db.<zone>           (1 fichier par zone master)
Garde-fous : rendu pur (testable sans BIND), checkconf avant tout reload,
reload via exec allow-list, RBAC admin + audit cote API.
"""
from __future__ import annotations
import json
import time
from pathlib import Path

CONF_DIR = Path("/etc/bind/infraos")
NAMED_CONF = Path("/etc/bind/named.conf")
INCLUDE_LINE = 'include "/etc/bind/infraos/named.conf.infraos";'


def serial_now(existing: int = 0) -> int:
    base = int(time.strftime("%Y%m%d00"))
    return max(base, existing + 1)


def render_zone(zone: dict, records: list[dict], serial: int) -> str:
    ttl = int(zone.get("ttl", 3600))
    origin = zone["name"] + "."
    lines = [f"$ORIGIN {origin}", f"$TTL {ttl}",
             f"@ IN SOA ns1.{origin} admin.{origin} (",
             f"    {serial} ; serial", "    3600 ; refresh",
             "    600 ; retry", "    86400 ; expire", "    600 ) ; minimum", ""]
    for r in records:
        t = r["rtype"]
        nm = r["name"]
        ttl_s = f" {r['ttl']}" if r.get("ttl") else ""
        if t == "MX":
            lines.append(f"{nm}{ttl_s} IN MX {r['priority']} {r['value']}.".replace("..", "."))
        elif t == "TXT":
            lines.append(f'{nm}{ttl_s} IN TXT "{r["value"]}"')
        elif t in ("CNAME", "NS", "PTR"):
            lines.append(f"{nm}{ttl_s} IN {t} {r['value']}.".replace("..", "."))
        else:
            lines.append(f"{nm}{ttl_s} IN {t} {r['value']}")
    return "\n".join(lines) + "\n"


def render_named_conf(zones: list[dict], forwarders: list[str], serials: dict) -> str:
    out = ["// Genere par InfraOS — ne pas editer", ""]
    if forwarders:
        fwd = " ".join(f"{f};" for f in forwarders)
        out += ['options {', '    directory "/var/cache/bind";',
                '    recursion yes;', f'    forwarders {{ {fwd} }};',
                '    forward only;', '};', ""]
    for z in zones:
        if not z.get("enabled", True):
            continue
        zn = z["name"]
        if z.get("kind") == "forward":
            fwd = " ".join(f"{f};" for f in json.loads(z.get("forwarders") or "[]"))
            out += [f'zone "{zn}" {{', '    type forward;',
                    f'    forwarders {{ {fwd} }};', '};', ""]
        else:
            out += [f'zone "{zn}" {{', '    type master;',
                    f'    file "/etc/bind/infraos/db.{zn}";', '};', ""]
    return "\n".join(out)


def write_and_check(zones: list[dict], by_zone: dict, forwarders: list[str],
                    serials: dict, conf_dir: Path = CONF_DIR) -> dict:
    """Ecrit fichiers + named-checkconf. Ne recharge PAS (apply separe)."""
    from .exec import run
    conf_dir.mkdir(parents=True, exist_ok=True)
    for z in zones:
        if z.get("kind") != "forward" and z.get("enabled", True):
            (conf_dir / f"db.{z['name']}").write_text(
                render_zone(z, by_zone.get(z["name"], []), serials.get(z["name"], serial_now())))
    (conf_dir / "named.conf.infraos").write_text(
        render_named_conf(zones, forwarders, serials))
    # rattache l'include au named.conf principal (backup, idempotent)
    try:
        current = NAMED_CONF.read_text() if NAMED_CONF.exists() else ""
        if INCLUDE_LINE not in current:
            bak = str(NAMED_CONF) + ".infraos-bak"
            Path(bak).write_text(current)
            with open(NAMED_CONF, "a") as f:
                f.write("\n" + INCLUDE_LINE + "\n")
    except OSError as e:
        return {"ok": False, "detail": f"include impossible: {e}"}
    r = run("named-checkconf", "/etc/bind/named.conf", timeout=30, caller="dns.render")
    return {"ok": r.rc == 0, "detail": r.out[-2000:] or ("checkconf OK" if r.rc == 0 else "checkconf KO")}


def reload() -> dict:
    from .exec import run
    r = run("rndc", "reload", timeout=60, caller="dns.reload")
    return {"rc": r.rc, "detail": r.out[-1000:]}
