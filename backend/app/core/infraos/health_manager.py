# SPDX-License-Identifier: GPL-3.0-or-later
"""Sante du systeme — agrege DB, Redis, disque, memoire, services, updates.

Statuts: ok | degraded | down. Lecture seule, sans exception.
"""
from __future__ import annotations
import time
from . import system as sysinfo
from .logging_conf import get_logger

log = get_logger("infraos.health")
CRITICAL_SERVICES = ["ssh", "infraos-api"]


def check() -> dict:
    t0 = time.time()
    checks: dict[str, dict] = {}
    worst = "ok"

    def mark(name: str, ok: bool, detail: str = ""):
        nonlocal worst
        st = "ok" if ok else "fail"
        checks[name] = {"status": st, "detail": detail}
        if not ok:
            worst = "degraded" if worst == "ok" else worst

    # DB
    try:
        from .db import get_session
        s = get_session()
        try:
            s.execute(__import__("sqlalchemy").text("SELECT 1"))
            mark("db", True, "requete SELECT 1 OK")
        finally:
            s.close()
    except Exception as e:
        mark("db", False, str(e)[:200])
        worst = "down"

    # Redis (optionnel : degrade seulement)
    try:
        from . import cache as cache_mod
        mark("cache", True, f"backend={cache_mod.backend()}")
    except Exception as e:
        mark("cache", False, str(e)[:200])

    # Disque / memoire
    try:
        import psutil
        du = psutil.disk_usage("/")
        mark("disk", du.percent < 90, f"{du.percent}% utilises")
        if du.percent >= 90:
            worst = "degraded"
        vm = psutil.virtual_memory()
        mark("memory", vm.percent < 95, f"{vm.percent}% utilises")
    except Exception as e:
        mark("metrics", False, str(e)[:200])

    # Services critiques
    try:
        states = {s["name"]: s["active"] for s in sysinfo.services_status()}
        bad = [c for c in CRITICAL_SERVICES if states.get(c) != "active"]
        mark("services", not bad,
             "critiques OK" if not bad else f"inactifs: {bad}")
        if bad:
            worst = "degraded"
    except Exception as e:
        mark("services", False, str(e)[:200])

    ms = int((time.time() - t0) * 1000)
    out = {"status": worst, "checks": checks, "duration_ms": ms}
    if worst != "ok":
        try:
            from .event_manager import publish
            publish("health.degraded", "health-manager", f"status={worst}")
        except Exception:
            pass
    return out
