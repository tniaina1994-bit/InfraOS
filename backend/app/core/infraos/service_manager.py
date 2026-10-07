# SPDX-License-Identifier: GPL-3.0-or-later
"""Gestion des services systemd — lecture + mutations admin auditees.

Mutations (start/stop/restart/enable/disable) : nom valide contre la liste
fermee (services des manifests + constantes), RBAC admin cote API, audit.
Jamais de nom libre vers systemctl.
"""
from __future__ import annotations
import re
from .exec import run
from . import system as sysinfo
from .audit import audit
from .logging_conf import get_logger

log = get_logger("infraos.services")
_NAME = re.compile(r"^[A-Za-z0-9@:._-]+$")
MUTATIONS = {"start", "stop", "restart", "enable", "disable"}


def known_services() -> set[str]:
    names = set(sysinfo.IMPORTANT_SERVICES)
    try:
        from . import module_manager as mm
        for m in mm.discover():
            for s in m.get("services", []) or []:
                if _NAME.match(str(s)):
                    names.add(str(s))
    except Exception:
        pass
    # instances WireGuard declarees en DB (wg-quick@wg0...) — validees par regex
    try:
        from .db import get_session
        from .models import VpnServer
        s = get_session()
        try:
            for v in s.query(VpnServer).all():
                if re.match(r"^wg[0-9]+$", v.name or ""):
                    names.add(f"wg-quick@{v.name}")
        finally:
            s.close()
    except Exception:
        pass
    return names


def control(service: str, action: str, actor: str = "api") -> dict:
    if action not in MUTATIONS:
        raise ValueError(f"action interdite: {action}")
    if not _NAME.match(service or "") or service not in known_services():
        raise ValueError(f"service inconnu ou interdit: {service}")
    r = run("systemctl", action, service, timeout=60, caller=f"service.{actor}")
    audit(f"service {action} {service} actor={actor} rc={r.rc}")
    log.info("service %s %s actor=%s rc=%s", action, service, actor, r.rc)
    return {"service": service, "action": action, "rc": r.rc,
            "detail": r.out[-1000:]}
