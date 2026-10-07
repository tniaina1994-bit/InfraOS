# SPDX-License-Identifier: GPL-3.0-or-later
"""Jobs/taches async — file Redis quand dispo, table DB sinon.

API: enqueue(kind, payload) -> job_id ; run_sync(job_id) execute les kinds
connus (updates.check). Worker dedie prevu quand Redis est la.
"""
from __future__ import annotations
import json
from . import cache as cache_mod
from .db import get_session
from .models import Job


def enqueue(kind: str, payload: dict | None = None) -> int:
    s = get_session()
    j = Job(kind=kind, payload=json.dumps(payload or {}))
    s.add(j)
    s.commit()
    jid = j.id
    s.close()
    # miroir file Redis (best-effort)
    try:
        r = cache_mod._redis()
        if r is not None:
            r.lpush("infraos:jobs", str(jid))
    except Exception:
        pass
    return jid


def run_sync(job_id: int) -> dict:
    s = get_session()
    j = s.get(Job, job_id)
    if not j:
        s.close()
        raise ValueError("job inconnu")
    j.status = "running"
    s.commit()
    try:
        if j.kind == "updates.check":
            from .updates import check_updates
            res = check_updates()
        else:
            res = {"detail": f"kind {j.kind} non implemente (worker futur)"}
        j.status = "done"
        j.result = json.dumps(res)[:4000]
    except Exception as e:
        j.status = "error"
        j.result = str(e)[:1000]
    s.commit()
    out = {"id": j.id, "kind": j.kind, "status": j.status}
    s.close()
    return out


def get_job(job_id: int) -> dict:
    import json as _j
    s = get_session()
    j = s.get(Job, job_id)
    if not j:
        s.close()
        raise ValueError("job inconnu")
    out = {"id": j.id, "kind": j.kind, "status": j.status,
           "result": _j.loads(j.result) if j.result else None}
    s.close()
    return out
