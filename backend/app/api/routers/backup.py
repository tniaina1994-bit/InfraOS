"""Backup — jobs restic/borg/rsync, runs, restore cible restreinte, cron (admin)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import json
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.db import get_session
from infraos.models import BackupJob, BackupRun
from infraos import backup as bk
from infraos import event_manager as em
from deps import require_role

router = APIRouter()


class JobBody(BaseModel):
    name: str
    backend: str = "restic"
    repo: str = ""
    sources: list[str] = []
    schedule: str = ""
    retention: str = "--keep-daily 7 --keep-weekly 4"
    encrypted: bool = True
    enabled: bool = True


class RestoreBody(BaseModel):
    snapshot: str = "latest"
    target: str = "/tmp/restore/"


def _out(j) -> dict:
    return {"id": j.id, "name": j.name, "backend": j.backend, "repo": j.repo,
            "sources": json.loads(j.sources or "[]"), "schedule": j.schedule,
            "retention": j.retention, "encrypted": j.encrypted, "enabled": j.enabled}


@router.get("/jobs")
def list_jobs(user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        return {"jobs": [_out(j) for j in db.query(BackupJob).all()]}
    finally:
        db.close()


@router.post("/jobs")
def create_job(body: JobBody, user: dict = Depends(require_role("admin"))):
    try:
        clean = bk.validate_job(body.backend, body.repo, body.sources)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db = get_session()
    try:
        if db.query(BackupJob).filter_by(name=body.name).first():
            raise HTTPException(409, "job existe")
        j = BackupJob(name=body.name, schedule=body.schedule,
                      retention=body.retention, encrypted=body.encrypted,
                      enabled=body.enabled, sources=json.dumps(clean["sources"]),
                      backend=clean["backend"], repo=clean["repo"])
        db.add(j)
        db.commit()
        return _out(j)
    finally:
        db.close()


@router.post("/jobs/{jid}/run")
def run_backup(jid: int, user: dict = Depends(require_role("admin"))):
    try:
        out = bk.run_job(jid)
    except ValueError as e:
        raise HTTPException(404, str(e))
    em.publish("job.done" if out["status"] == "done" else "job.error",
               user["username"], f"backup {jid} {out['status']}")
    return out


@router.get("/jobs/{jid}/runs")
def list_runs(jid: int, user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        rows = (db.query(BackupRun).filter_by(job_id=jid)
                .order_by(BackupRun.id.desc()).limit(10).all())
        return {"runs": [{"id": r.id, "status": r.status,
                         "created_at": str(r.created_at),
                         "finished_at": str(r.finished_at) if r.finished_at else None,
                         "log": (r.log or "")[-2000:]} for r in rows]}
    finally:
        db.close()


@router.post("/jobs/{jid}/restore")
def restore_backup(jid: int, body: RestoreBody,
                   user: dict = Depends(require_role("admin"))):
    try:
        out = bk.restore(jid, body.snapshot, body.target)
    except ValueError as e:
        raise HTTPException(400, str(e))
    em.publish("job.done", user["username"], f"restore {jid} -> {body.target}")
    return out


@router.post("/cron/apply")
def cron_apply(user: dict = Depends(require_role("admin"))):
    try:
        Path("/etc/cron.d/infraos-backup").write_text(bk.render_cron())
    except OSError as e:
        raise HTTPException(500, str(e))
    return {"applied": True, "cron": bk.render_cron()}
