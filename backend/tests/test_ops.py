"""Tests API: discovery, monitoring, shares, backup (RBAC + validation)."""
import os
import sys
from pathlib import Path

TMPDB = "/tmp/infraos-test-ops.db"
if os.path.exists(TMPDB):
    os.remove(TMPDB)
os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
os.environ["INFRAOS_ADMIN_PASSWORD"] = "Testpw123456"
os.environ["INFRAOS_JWT_SECRET"] = "test-secret-32-chars-minimum-xyz"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "core"))

from infraos import db as dbmod


def _ensure():
    os.environ["INFRAOS_RATE_LOGIN_N"] = "1000"
    try:
        from ratelimit import reset as _rlreset
        _rlreset()
    except Exception:
        pass
    os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
    dbmod._engine = None
    dbmod._SessionFactory = None
    from infraos.db import init_db as _init, get_session as _sess
    from infraos.models import User as _User
    from infraos.security import hash_password as _hash
    _init(os.environ["INFRAOS_DB_URL"])
    _db = _sess()
    if not _db.query(_User).filter_by(username="admin").first():
        _db.add(_User(username="admin", password_hash=_hash("Testpw123456"), role="admin"))
        _db.commit()
    _db.close()


_ensure()

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(autouse=True)
def _isolated():
    _ensure()
    yield


@pytest.fixture()
def auth():
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/login", json={"username": "admin", "password": "Testpw123456"})
        assert r.status_code == 200
        return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_discovery_guards_and_arp(auth):
    with TestClient(app) as c:
        assert c.post("/api/v1/discovery/scans",
                      json={"target": "0.0.0.0/0"}, headers=auth).status_code == 400
        r = c.get("/api/v1/discovery/arp", headers=auth)
        assert r.status_code == 200 and "entries" in r.json()
        r = c.get("/api/v1/discovery/compare?a=1&b=2", headers=auth)
        assert r.status_code == 200 and "new" in r.json()


def test_monitoring_flow(auth):
    with TestClient(app) as c:
        assert c.get("/api/v1/monitoring/current", headers=auth).status_code == 200
        assert c.post("/api/v1/monitoring/collect", headers=auth).status_code == 200
        r = c.get("/api/v1/monitoring/history", headers=auth)
        assert len(r.json()["samples"]) >= 1
        assert c.post("/api/v1/monitoring/agents",
                      json={"hostname": "pc1", "os": "windows",
                            "token": "token-1234567890"}, headers=auth).status_code == 200
        assert c.post("/api/v1/monitoring/agents/push",
                      json={"hostname": "pc1", "token": "bad", "metrics": {}}).status_code == 401


def test_shares_flow(auth):
    with TestClient(app) as c:
        assert c.post("/api/v1/shares/shares",
                      json={"name": "global", "path": "/srv/x"}, headers=auth).status_code == 400
        r = c.post("/api/v1/shares/shares",
                   json={"name": "docs", "path": "/srv/docs-test"}, headers=auth)
        assert r.status_code == 200


def test_backup_flow(auth):
    with TestClient(app) as c:
        assert c.post("/api/v1/backup/jobs",
                      json={"name": "j", "backend": "tar", "repo": "/r",
                            "sources": ["/x"]}, headers=auth).status_code == 400
        r = c.post("/api/v1/backup/jobs",
                   json={"name": "j", "backend": "restic", "repo": "/tmp/bk-test",
                         "sources": ["/etc/hostname"]}, headers=auth)
        jid = r.json()["id"]
        assert c.post(f"/api/v1/backup/jobs/{jid}/restore",
                      json={"target": "/etc/evil"}, headers=auth).status_code == 400
