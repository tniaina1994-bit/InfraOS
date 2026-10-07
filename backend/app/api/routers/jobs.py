"""Jobs async — enqueue + statut (Redis si present, DB sinon)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos import tasks, cache as cache_mod
from infraos import task_manager as tm
from infraos import event_manager as em
from deps import require_role

router = APIRouter()


class EnqueueBody(BaseModel):
    kind: str = "updates.check"
    payload: dict = {}
    sync: bool = True


@router.post("")
def enqueue_job(body: EnqueueBody, user: dict = Depends(require_role("operator"))):
    jid = tasks.enqueue(body.kind, body.payload)
    out = {"id": jid, "cache_backend": cache_mod.backend()}
    if body.sync:
        out.update(tasks.run_sync(jid))
        try:
            em.publish("job.done" if out.get("status") == "done" else "job.error",
                       user["username"], f"{body.kind} id={jid}")
        except Exception:
            pass
    return out


@router.get("")
def list_jobs(limit: int = 20, user: dict = Depends(require_role("operator"))):
    return {"jobs": tm.list_recent(limit)}


@router.delete("/{job_id}")
def cancel_job(job_id: int, user: dict = Depends(require_role("operator"))):
    try:
        return tm.cancel(job_id)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(400, str(e))


@router.get("/{job_id}")
def job_status(job_id: int, user: dict = Depends(require_role("operator"))):
    return tasks.get_job(job_id)
