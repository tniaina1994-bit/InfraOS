# SPDX-License-Identifier: GPL-3.0-or-later
"""Task Manager — facade (impl: tasks.py, file Redis ou table DB)."""
from .tasks import enqueue, run_sync, get_job  # noqa: F401
from .models import Job  # noqa: F401
from .db import get_session as _sess


def list_recent(limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit), 100))
    s = _sess()
    try:
        rows = s.query(Job).order_by(Job.id.desc()).limit(limit).all()
        return [{"id": j.id, "kind": j.kind, "status": j.status} for j in rows]
    finally:
        s.close()


def cancel(job_id: int) -> dict:
    s = _sess()
    try:
        j = s.get(Job, job_id)
        if not j:
            raise ValueError("job inconnu")
        if j.status != "queued":
            raise ValueError(f"annulation impossible (status={j.status})")
        j.status = "error"
        j.result = "annule par operateur"
        s.commit()
        return {"id": j.id, "status": j.status}
    finally:
        s.close()


__all__ = ["enqueue", "run_sync", "get_job", "list_recent", "cancel"]
