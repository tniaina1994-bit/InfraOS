"""Tests API: config/events/health/services-mutations/tasks (RBAC inclus)."""
import os
import sys
from pathlib import Path

TMPDB = "/tmp/infraos-test-managers.db"
if os.path.exists(TMPDB):
    os.remove(TMPDB)
os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
os.environ["INFRAOS_ADMIN_PASSWORD"] = "testpw123"
os.environ["INFRAOS_JWT_SECRET"] = "test-secret-32-chars-minimum-xyz"
os.environ["INFRAOS_DATA_DIR"] = "/tmp/infraos-test-mgrstate"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "core"))

from infraos import db as dbmod


def _ensure():
    os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
    os.environ["INFRAOS_DATA_DIR"] = "/tmp/infraos-test-mgrstate"
    dbmod._engine = None
    dbmod._SessionFactory = None
    from infraos.db import init_db as _init, get_session as _sess
    from infraos.models import User as _User
    from infraos.security import hash_password as _hash
    _init(os.environ["INFRAOS_DB_URL"])
    _db = _sess()
    if not _db.query(_User).filter_by(username="admin").first():
        _db.add(_User(username="admin", password_hash=_hash("testpw123"), role="admin"))
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
    # portee fonction : login APRES l'isolation autouse (sinon session dans la mauvaise DB)
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/login", json={"username": "admin", "password": "testpw123"})
        assert r.status_code == 200
        return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health_detail(auth):
    with TestClient(app) as c:
        r = c.get("/api/v1/system/health", headers=auth)
        assert r.status_code == 200 and r.json()["status"] in ("ok", "degraded", "down")


def test_config_roundtrip(auth):
    with TestClient(app) as c:
        r = c.get("/api/v1/config", headers=auth)
        assert r.status_code == 200 and r.json()["jwt_secret"] == "***"
        assert c.get("/api/v1/config").status_code in (401, 403)
        r = c.put("/api/v1/config", json={"jwt_expire_min": 90}, headers=auth)
        assert r.status_code == 200 and r.json()["jwt_expire_min"] == 90
        r = c.put("/api/v1/config", json={"jwt_expire_min": 99999}, headers=auth)
        assert r.status_code == 400
        c.put("/api/v1/config", json={"jwt_expire_min": 60}, headers=auth)


def test_events_feed(auth):
    with TestClient(app) as c:
        r = c.get("/api/v1/events?limit=10", headers=auth)
        assert r.status_code == 200 and "events" in r.json() and "types" in r.json()
        assert c.get("/api/v1/events").status_code in (401, 403)


def test_service_mutation_guards(auth):
    with TestClient(app) as c:
        # service inconnu refuse (400, pas d'execution)
        r = c.post("/api/v1/services/ghost-xyz/restart", headers=auth)
        assert r.status_code == 400
        # sans token refuse
        assert c.post("/api/v1/services/cron/restart").status_code in (401, 403)


def test_tasks_list_cancel(auth):
    with TestClient(app) as c:
        r = c.post("/api/v1/jobs", json={"kind": "updates.check", "sync": False}, headers=auth)
        jid = r.json()["id"]
        r = c.get("/api/v1/jobs", headers=auth)
        assert r.status_code == 200 and any(j["id"] == jid for j in r.json()["jobs"])
        r = c.delete(f"/api/v1/jobs/{jid}", headers=auth)
        assert r.status_code == 200
