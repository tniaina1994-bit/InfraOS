# SPDX-License-Identifier: GPL-3.0-or-later
"""Backup Manager — restic/borgbackup/rsync (100% open source).

Jobs (DB) -> execution auditee (admin), logs fichier, retention, restore
cible restreinte, schedules via cron.d (apply). PBS : prevu (docs/BACKUP.md).
"""
from __future__ import annotations
import json
import os
import re
import shlex
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path
from .db import get_session
from .models import BackupJob, BackupRun
from .logging_conf import get_logger

log = get_logger("infraos.backup")
LOGDIR = Path("/var/log/infraos/backups")
PWDIR = Path("/etc/infraos/backup-pw")
BACKENDS = {"restic", "borg", "rsync"}
_RESTORE_ROOTS = ("/var/lib/infraos/restore/", "/tmp/")


def validate_job(backend: str, repo: str, sources: list) -> dict:
    if backend not in BACKENDS:
        raise ValueError(f"backend: {sorted(BACKENDS)}")
    repo = (repo or "").strip()
    if backend == "rsync":
        if not repo.startswith("/") or ".." in repo:
            raise ValueError("repo rsync : chemin absolu requis")
    else:
        if not repo or len(repo) > 255 or ".." in repo:
            raise ValueError("repo invalide")
    srcs = []
    for s in sources or []:
        if not isinstance(s, str) or not s.startswith("/") or ".." in s:
            raise ValueError(f"source invalide: {s}")
        srcs.append(s)
    if not srcs:
        raise ValueError("au moins une source requise")
    return {"backend": backend, "repo": repo, "sources": srcs}


def _pw_file(job_id: int) -> Path:
    import secrets
    PWDIR.mkdir(parents=True, exist_ok=True)
    p = PWDIR / f"{job_id}.pw"
    if not p.exists():
        p.write_text(secrets.token_urlsafe(32))
        os.chmod(p, 0o600)
    return p


def _run(cmd: list[str], env: dict, logpath: Path, timeout: int = 1800) -> int:
    LOGDIR.mkdir(parents=True, exist_ok=True)
    with open(logpath, "a") as lf:
        lf.write(f"$ {' '.join(shlex.quote(c) for c in cmd)}\n")
        lf.flush()
        p = subprocess.run(cmd, env=env, stdout=lf, stderr=subprocess.STDOUT,
                           timeout=timeout, shell=False)
        return p.returncode


def run_job(job_id: int, timeout: int = 1800) -> dict:
    s = get_session()
    try:
        job = s.get(BackupJob, job_id)
        if not job:
            raise ValueError("job inconnu")
        spec = {"backend": job.backend, "repo": job.repo,
                "sources": json.loads(job.sources or "[]"),
                "retention": job.retention, "encrypted": job.encrypted}
        run = BackupRun(job_id=job_id, status="running")
        s.add(run)
        s.commit()
        rid = run.id
    finally:
        s.close()
    logpath = LOGDIR / f"{rid}.log"
    env = dict(os.environ)
    try:
        if spec["backend"] == "restic":
            rc = _restic(spec, logpath, timeout, job_id)
        elif spec["backend"] == "borg":
            rc = _borg(spec, logpath, timeout, job_id)
        else:
            rc = _rsync(spec, logpath, timeout)
        status = "done" if rc == 0 else "error"
    except Exception as e:
        rc, status = 1, "error"
        LOGDIR.mkdir(parents=True, exist_ok=True)
        with open(logpath, "a") as lf:
            lf.write(f"ERREUR: {e}\n")
    s = get_session()
    try:
        r = s.get(BackupRun, rid)
        r.status = status
        try:
            r.log = logpath.read_text()[-8000:]
        except OSError:
            pass
        r.finished_at = datetime.now(timezone.utc)
        s.commit()
    finally:
        s.close()
    return {"run_id": rid, "status": status}


def _restic(spec: dict, logpath: Path, timeout: int, job_id: int) -> int:
    exe = shutil.which("restic")
    if not exe:
        raise ValueError("restic absent")
    env = dict(os.environ)
    if spec["encrypted"]:
        env["RESTIC_PASSWORD_FILE"] = str(_pw_file(job_id))
    else:
        env["RESTIC_PASSWORD"] = "infraos-insecure"
    rc = _run([exe, "-r", spec["repo"], "cat", "config"], env, logpath, 60)
    if rc != 0:
        rc = _run([exe, "-r", spec["repo"], "init"], env, logpath, 120)
        if rc != 0:
            return rc
    rc = _run([exe, "-r", spec["repo"], "backup", *spec["sources"]], env, logpath, timeout)
    if rc != 0:
        return rc
    if spec.get("retention"):
        import shlex as _sh
        rc = _run([exe, "-r", spec["repo"], "forget", "--prune",
                   *_sh.split(spec["retention"])], env, logpath, 600)
    return rc


def _borg(spec: dict, logpath: Path, timeout: int, job_id: int) -> int:
    exe = shutil.which("borg")
    if not exe:
        raise ValueError("borg absent")
    env = dict(os.environ)
    env["BORG_PASSPHRASE"] = _pw_file(job_id).read_text() if spec["encrypted"] else "infraos-insecure"
    env["BORG_REPO"] = spec["repo"]
    rc = _run([exe, "info", spec["repo"]], env, logpath, 60)
    if rc != 0:
        rc = _run([exe, "init", "--encryption=repokey", spec["repo"]], env, logpath, 120)
        if rc != 0:
            return rc
    import time
    rc = _run([exe, "create", "--stats",
               f"{spec['repo']}::infraos-{time.strftime('%Y%m%d-%H%M%S')}",
               *spec["sources"]], env, logpath, timeout)
    if rc != 0:
        return rc
    if spec.get("retention"):
        import shlex as _sh
        # retention borg : --keep-daily N ... (sans --prune exact restic)
        rc = _run([exe, "prune", spec["repo"], *_sh.split(
            spec["retention"].replace("--keep-", "--keep-"))], env, logpath, 600)
    return rc


def _rsync(spec: dict, logpath: Path, timeout: int) -> int:
    exe = shutil.which("rsync")
    if not exe:
        raise ValueError("rsync absent")
    Path(spec["repo"]).mkdir(parents=True, exist_ok=True)
    return _run([exe, "-a", "--delete", *spec["sources"], spec["repo"] + "/"],
                dict(os.environ), logpath, timeout)


def restore(job_id: int, snapshot: str, target: str) -> dict:
    """Restauration cible restreinte (/var/lib/infraos/restore/ ou /tmp/)."""
    if not target.startswith(_RESTORE_ROOTS) or ".." in target:
        raise ValueError(f"cible restreinte a {list(_RESTORE_ROOTS)}")
    s = get_session()
    try:
        job = s.get(BackupJob, job_id)
        if not job:
            raise ValueError("job inconnu")
        spec = {"backend": job.backend, "repo": job.repo, "encrypted": job.encrypted}
    finally:
        s.close()
    Path(target).mkdir(parents=True, exist_ok=True)
    LOGDIR.mkdir(parents=True, exist_ok=True)
    logpath = LOGDIR / f"restore-{job_id}.log"
    env = dict(os.environ)
    if spec["backend"] == "restic":
        exe = shutil.which("restic")
        if spec["encrypted"]:
            env["RESTIC_PASSWORD_FILE"] = str(PWDIR / f"{job_id}.pw")
        rc = _run([exe, "-r", spec["repo"], "restore", snapshot or "latest",
                   "--target", target], env, logpath)
    elif spec["backend"] == "borg":
        exe = shutil.which("borg")
        env["BORG_PASSPHRASE"] = (PWDIR / f"{job_id}.pw").read_text() if spec["encrypted"] else "infraos-insecure"
        rc = _run([exe, "extract", f"{spec['repo']}::{snapshot or 'latest'}",
                   "--strip-components", "0"], {**env, "BORG_CWD": target}, logpath)
    else:
        exe = shutil.which("rsync")
        rc = _run([exe, "-a", spec["repo"] + "/", target + "/"], env, logpath)
    return {"rc": rc, "target": target, "log": str(logpath)}


def render_cron() -> str:
    s = get_session()
    try:
        jobs = [j for j in s.query(BackupJob).all() if j.enabled and j.schedule]
    finally:
        s.close()
    lines = ["# Genere par InfraOS — ne pas editer"]
    for j in jobs:
        if not re.match(r"^[\w*/,\- ]{1,64}$", j.schedule):
            continue
        lines.append(f"{j.schedule} root /usr/local/sbin/infraos-backup-run {j.id}")
    return "\n".join(lines) + "\n"
