# SPDX-License-Identifier: GPL-3.0-or-later
"""DNS Manager — BIND9 Debian (zones + records + forwarders + apply).

Backend Samba AD DLZ : prevu (docs/DNS.md) — si sam.ldb provisionne,
status() le signale et l'apply DLZ reste documente mais non execute en v1.
"""
from __future__ import annotations
import ipaddress
import json
from pathlib import Path
import yaml
from ..module_base import SimpleServiceModule, ModuleStatus
from ..db import get_session
from ..models import DnsZone, DnsRecord
from .. import dns_validate as dv
from .. import dns_render as rnd
from .. import packages as pkg

DNS_YAML = Path("/etc/infraos/dns.yaml")


def get_forwarders() -> list[str]:
    try:
        if DNS_YAML.exists():
            return (yaml.safe_load(DNS_YAML.read_text()) or {}).get("forwarders", [])
    except OSError:
        pass
    return []


def set_forwarders(fwd: list[str]) -> list[str]:
    clean = []
    for f in fwd:
        try:
            ipaddress.ip_address(f)
        except ValueError:
            raise ValueError(f"forwarder invalide: {f}")
        clean.append(f)
    try:
        DNS_YAML.parent.mkdir(parents=True, exist_ok=True)
        DNS_YAML.write_text(yaml.safe_dump({"forwarders": clean}, default_flow_style=False))
        import os
        os.chmod(DNS_YAML, 0o600)
    except OSError as e:
        raise ValueError(f"persistance impossible: {e}")
    return clean


def backend_kind() -> dict:
    """files (BIND9 natif v1) vs samdb_dlz (prevu si AD provisionne)."""
    import os
    ad = os.path.exists("/var/lib/samba/private/sam.ldb")
    return {"active": "files",
            "samba_dlz": "planned" if not ad else "available-manual",
            "detail": "BIND9 fichiers v1 ; DLZ si AD provisionne (docs/DNS.md)"}


class DnsModule(SimpleServiceModule):
    name = "dns"
    SERVICE = "named"
    PACKAGE = "bind9"
    PLANNED = ["dlz"]

    def status(self) -> ModuleStatus:
        base = super().status()
        try:
            s = get_session()
            try:
                nz = s.query(DnsZone).count()
                nr = s.query(DnsRecord).count()
            finally:
                s.close()
            base.detail += f" | {nz} zones, {nr} records (DB)"
        except Exception as e:
            base.detail += f" | DB: {e}"
        base.detail += f" | backend={backend_kind()['active']}"
        return base

    def actions(self) -> list[str]:
        return ["status", "forwarders", "apply", "backend", "dlz"]

    def run_action(self, action: str, params: dict | None = None):
        params = params or {}
        if action == "status":
            st = self.status()
            return {"installed": st.installed, "running": st.running, "detail": st.detail}
        if action == "forwarders":
            return {"forwarders": get_forwarders()}
        if action == "backend":
            return backend_kind()
        if action == "apply":
            return apply()
        return super().run_action(action, params)


def apply() -> dict:
    """Rend + checkconf + reload (checkconf DOIT reussir avant reload)."""
    s = get_session()
    try:
        zones = [{"id": z.id, "name": z.name, "kind": z.kind, "reverse": z.reverse,
                  "ttl": z.ttl, "forwarders": z.forwarders, "enabled": z.enabled}
                 for z in s.query(DnsZone).all()]
        by_zone = {}
        for z in zones:
            recs = s.query(DnsRecord).filter_by(zone_id=z["id"]).all()
            by_zone[z["name"]] = [{"id": r.id, "name": r.name, "rtype": r.rtype,
                                   "value": r.value, "priority": r.priority, "ttl": r.ttl}
                                  for r in recs]
    finally:
        s.close()
    serials = {z["name"]: rnd.serial_now() for z in zones}
    res = rnd.write_and_check(zones, by_zone, get_forwarders(), serials)
    if not res["ok"]:
        return {"applied": False, "stage": "checkconf", **res}
    rel = rnd.reload()
    return {"applied": rel["rc"] == 0, "stage": "reload",
            "serials": serials, "check": res["detail"], "reload": rel["detail"]}
