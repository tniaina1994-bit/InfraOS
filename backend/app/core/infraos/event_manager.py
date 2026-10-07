# SPDX-License-Identifier: GPL-3.0-or-later
"""Bus d'evenements in-process du monolithe (pas de broker externe requis).

publish() -> table audit_events (Postgres/SQLite) + bus memoire + pubsub
Redis best-effort. Types fermes (EVENT_TYPES), acteur/audit systematiques.
Consommateurs v1 : GET /api/v1/events (UI), futurs : notifications, webhooks.
"""
from __future__ import annotations
from collections import deque
import json
from .audit import audit as audit_file
from .logging_conf import get_logger

log = get_logger("infraos.events")

EVENT_TYPES = {
    "user.login", "user.logout", "user.created", "user.disabled", "user.password",
    "group.created", "group.member",
    "module.enabled", "module.disabled", "module.installed", "module.uninstalled",
    "service.action", "config.updated",
    "updates.available", "job.done", "job.error",
    "health.degraded",
    # Identity & Domain Controller
    "identity.domain.setup", "identity.domain.backup", "identity.domain.uninstall",
    "identity.user.created", "identity.user.updated", "identity.user.deleted",
    "identity.user.enabled", "identity.user.disabled", "identity.user.password",
    "identity.user.unlocked", "identity.user.moved",
    "identity.group.created", "identity.group.updated", "identity.group.deleted",
    "identity.group.members",
    "identity.ou.created", "identity.ou.deleted", "identity.ou.moved",
    "identity.ou.renamed",
    "identity.computer.created", "identity.computer.deleted", "identity.computer.moved",
    "identity.computer.enabled", "identity.computer.disabled",
    "identity.policy.changed", "identity.test.kerberos", "identity.test.dns",
}

_bus: deque = deque(maxlen=200)


def publish(etype: str, actor: str = "system", detail: str = "",
            resource: str = "", ip: str = "", result: str = "SUCCESS") -> dict:
    if etype not in EVENT_TYPES:
        raise ValueError(f"type d'evenement inconnu: {etype}")
    ev = {"type": etype, "actor": actor, "detail": detail[:1000],
          "resource": resource, "ip": ip, "result": result}
    _bus.append(ev)
    try:
        from .db import get_session
        from .models import AuditEvent
        s = get_session()
        try:
            s.add(AuditEvent(actor=actor, action=etype, detail=detail[:2000],
                             resource=resource[:255], ip=ip[:64], result=result))
            s.commit()
        finally:
            s.close()
    except Exception as e:
        log.error("event persist fail: %s", e)
    try:
        from . import cache as cache_mod
        r = cache_mod._redis()
        if r is not None:
            r.publish("infraos:events", json.dumps(ev))
    except Exception:
        pass
    try:
        audit_file(etype, actor=actor, resource=resource, ip=ip,
                   result=result, detail=detail[:200])
    except Exception:
        pass
    return ev


def recent(limit: int = 50) -> list[dict]:
    """Derniers evenements (DB d'abord, bus memoire en secours)."""
    limit = max(1, min(int(limit), 200))
    try:
        from .db import get_session
        from .models import AuditEvent
        s = get_session()
        try:
            rows = (s.query(AuditEvent).order_by(AuditEvent.id.desc())
                    .limit(limit).all())
            return [{"type": r.action, "actor": r.actor,
                     "detail": r.detail, "ts": str(r.ts),
                     "resource": r.resource, "ip": r.ip,
                     "result": r.result} for r in reversed(rows)]
        finally:
            s.close()
    except Exception:
        return list(_bus)[-limit:]
