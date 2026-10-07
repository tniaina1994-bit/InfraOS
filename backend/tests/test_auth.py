"""Tests API: login local, /me, RBAC, providers, jobs, logs."""
import os
import sys
from pathlib import Path

TMPDB = "/tmp/infraos-test-auth.db"
if os.path.exists(TMPDB):
    os.remove(TMPDB)
os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
os.environ["INFRAOS_ADMIN_PASSWORD"] = "testpw123"
os.environ["INFRAOS_JWT_SECRET"] = "test-secret-32-chars-minimum-xyz"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "core"))

from infraos import db as dbmod
from infraos.config import load_settings as _load
from infraos.db import init_db as _init, get_session as _sess
from infraos.models import User as _User
from infraos.security import hash_password as _hash


def _ensure_admin():
    """Rebind le moteur au TMPDB + seed admin — isole des tests voisins."""
    os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
    os.environ["INFRAOS_RATE_LOGIN_N"] = "1000"
    try:
        from ratelimit import reset as _rlreset
        _rlreset()
    except Exception:
        pass
    dbmod._engine = None
    dbmod._SessionFactory = None
    _init(os.environ["INFRAOS_DB_URL"])
    _db = _sess()
    if not _db.query(_User).filter_by(username="admin").first():
        _db.add(_User(username="admin", password_hash=_hash("testpw123"),
                      role="admin", display_name="Administrateur"))
        _db.commit()
    _db.close()


_ensure_admin()

import pytest


@pytest.fixture(autouse=True)
def _isolated_db():
    _ensure_admin()
    yield

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _token():
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "testpw123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_login_me():
    t = _token()
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t}"})
    assert r.status_code == 200 and r.json()["username"] == "admin"


def test_login_ko():
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "bad"})
    assert r.status_code == 401


def test_providers_shape():
    r = client.get("/api/v1/auth/providers")
    names = [p["name"] for p in r.json()["providers"]]
    assert names == ["local", "ldap", "ad", "kerberos"]


def test_users_rbac():
    t = _token()
    h = {"Authorization": f"Bearer {t}"}
    r = client.get("/api/v1/users", headers=h)
    assert r.status_code == 200
    r2 = client.get("/api/v1/users")
    assert r2.status_code in (401, 403)


def test_jobs_and_logs():
    t = _token()
    h = {"Authorization": f"Bearer {t}"}
    r = client.post("/api/v1/jobs", json={"kind": "updates.check", "sync": True}, headers=h)
    assert r.status_code == 200
    r = client.get("/api/v1/logs/journal?service=infraos-api&lines=5", headers=h)
    assert r.status_code == 200
