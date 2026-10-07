# SPDX-License-Identifier: GPL-3.0-or-later
"""Security Center — centralise logs systeme/auth/firewall/services,
evenements, echecs de login et activite suspecte (heuristiques sur l'audit).

Demarre avec journald + logs systeme. Integrations futures :
rsyslog (relai), Suricata (eve.json), Fail2ban (jails) — statut expose,
jamais obligatoire.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from .db import get_session
from .models import AuditEvent
from .exec import run
from . import packages as pkg


def _query(action_like: str | None = None, result: str | None = None,
           hours: int = 24, limit: int = 200) -> list:
    s = get_session()
    try:
        q = s.query(AuditEvent)
        if action_like:
            q = q.filter(AuditEvent.action.like(action_like))
        if result:
            q = q.filter_by(result=result)
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (q.filter(AuditEvent.ts >= since)
                .order_by(AuditEvent.id.desc()).limit(limit).all())
    finally:
        s.close()


def failed_logins(hours: int = 24, limit: int = 50) -> list[dict]:
    rows = _query("user.login%", hours=hours, limit=limit * 2)
    out = [ {"actor": r.actor, "detail": r.detail, "ip": r.ip,
              "ts": str(r.ts), "result": r.result}
            for r in rows if r.result != "SUCCESS"][:limit]
    return out


def suspicious(hours: int = 24) -> list[dict]:
    """Heuristiques simples et expliquees (pas de ML) :
    - >=5 echecs login meme IP / 15 min -> bruteforce suspect ;
    - login sur compte desactive/bloque ;
    - action admin hors modules connus (jamais ici : allow-list)."""
    out = []
    fails = _query("user.login%", hours=hours, limit=500)
    by_ip: dict[str, list] = {}
    for r in fails:
        if r.result == "SUCCESS" or not r.ip:
            continue
        by_ip.setdefault(r.ip, []).append(r)
    for ip, rows in by_ip.items():
        rows.sort(key=lambda r: str(r.ts))
        for i in range(len(rows)):
            window = [x for x in rows[i:]
                      if (x.ts - rows[i].ts).total_seconds() <= 900]
            if len(window) >= 5:
                out.append({"rule": "bruteforce",
                            "detail": f"{len(window)} echecs login depuis {ip} en 15 min",
                            "ip": ip, "ts": str(window[-1].ts)})
                break
    for r in fails:
        if "desactive" in (r.detail or "") or "revoque" in (r.detail or ""):
            out.append({"rule": "disabled-account", "detail": f"{r.actor}: {r.detail}",
                        "ip": r.ip, "ts": str(r.ts)})
    return out[:50]


def system_logs(lines: int = 100) -> dict:
    """Logs systeme journald (tous services, lecture seule)."""
    n = max(1, min(int(lines), 500))
    r = run("journalctl", "--no-pager", "-n", str(n), caller="security.logs")
    return {"rc": r.rc, "logs": r.out[-12000:]}


def firewall_logs(lines: int = 100) -> dict:
    """Logs noyau/pare-feu (journald kernel, contient les LOG nftables)."""
    n = max(1, min(int(lines), 200))
    r = run("journalctl", "--no-pager", "-k", "-n", str(n), caller="security.logs")
    keep = [l for l in r.out.splitlines()
            if "infraos" in l or "DROP" in l or "LOG" in l][-100:]
    return {"rc": r.rc, "logs": "\n".join(keep)[-8000:]}


def integrations() -> list[dict]:
    """Etat des integrations (actives ou prevues, jamais obligatoires)."""
    out = [{"name": "journald", "status": "active",
            "detail": "source principale (system/auth/firewall/services)"}]
    out.append({"name": "rsyslog",
                "status": "active" if pkg.is_installed("rsyslog").get("installed") else "planned",
                "detail": "relai syslog prevu (docs/LOGGING.md)"})
    import os
    eve = "/var/log/suricata/eve.json"
    out.append({"name": "suricata",
                "status": "active" if os.path.exists(eve) else "planned",
                "detail": f"IDS eve.json ({eve})"})
    fb = pkg.is_installed("fail2ban").get("installed", False)
    st = "unknown"
    if fb:
        st = run("systemctl", "is-active", "fail2ban", caller="security").out.strip() or "unknown"
    out.append({"name": "fail2ban", "status": "active" if st == "active" else "planned",
                "detail": f"paquet={fb}, service={st}"})
    return out


def overview() -> dict:
    fails = failed_logins(24, 50)
    susp = suspicious(24)
    try:
        from .updates import check_updates
        upd = check_updates()
    except Exception:
        upd = {"pending": 0}
    return {"failed_logins_24h": len(fails), "failed_logins": fails[:10],
            "suspicious": susp, "updates_pending": upd.get("pending", 0),
            "integrations": integrations()}
