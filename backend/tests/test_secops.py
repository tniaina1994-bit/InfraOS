"""Tests API: security center, updates complets, config structure."""
import os
import sys
from pathlib import Path

TMPDB = "/tmp/infraos-test-sec.db"
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


def test_failed_login_feeds_security(auth):
    with TestClient(app) as c:
        assert c.post("/api/v1/auth/login",
                      json={"username": "admin", "password": "mauvais-mdp-123"}).status_code == 401
        r = c.get("/api/v1/security/failed-logins", headers=auth)
        assert r.status_code == 200 and len(r.json()["failed"]) >= 1
        r = c.get("/api/v1/security/overview", headers=auth)
        assert r.json()["failed_logins_24h"] >= 1
        assert "integrations" in r.json()


def test_updates_endpoints(auth):
    with TestClient(app) as c:
        assert c.get("/api/v1/updates/list", headers=auth).status_code == 200
        assert c.get("/api/v1/updates/history", headers=auth).status_code == 200
        assert c.post("/api/v1/updates/install", json={"packages": []},
                      headers=auth).status_code == 400
        assert c.get("/api/v1/updates/package?name=zzz", headers=auth).status_code in (200, 400)


def test_apt_sources_endpoints(auth):
    with TestClient(app) as c:
        r = c.get("/api/v1/updates/sources", headers=auth)
        assert r.status_code == 200 and isinstance(r.json()["sources"], list)
        # validations : nom, URL, suite refuses avant toute ecriture disque
        assert c.post("/api/v1/updates/sources",
                      json={"name": "../evil", "url": "https://deb.example.org"},
                      headers=auth).status_code == 400
        assert c.post("/api/v1/updates/sources",
                      json={"name": "ok", "url": "ftp://insecure.example.org"},
                      headers=auth).status_code == 400
        assert c.post("/api/v1/updates/sources",
                      json={"name": "ok", "url": "https://deb.example.org",
                            "suite": "bookworm; rm -rf /"}, headers=auth).status_code == 400
        assert c.delete("/api/v1/updates/sources/inexistant", headers=auth).status_code == 400
        # RBAC : sans token = refuse
        assert c.get("/api/v1/updates/sources").status_code in (401, 403)


def test_full_upgrade_endpoint(auth, monkeypatch):
    from infraos import updates as um_mod
    called = {}

    def fake_full_upgrade(actor="api"):
        called["actor"] = actor
        return {"run_id": 0, "status": "done", "rc": 0, "detail": "fake"}

    monkeypatch.setattr(um_mod, "full_upgrade", fake_full_upgrade)
    with TestClient(app) as c:
        r = c.post("/api/v1/updates/full-upgrade", headers=auth)
        assert r.status_code == 200 and r.json()["status"] == "done"
        assert called.get("actor") == "admin"
        assert c.post("/api/v1/updates/full-upgrade").status_code in (401, 403)


def test_config_structure_endpoints(auth):
    with TestClient(app) as c:
        r = c.get("/api/v1/config/structure", headers=auth)
        assert r.status_code == 200
        r = c.get("/api/v1/config/modules/dns", headers=auth)
        assert r.status_code == 200 and "config" in r.json()
        assert c.put("/api/v1/config/modules/dns", json={"x": 1}, headers=auth).status_code == 200
        assert c.get("/api/v1/config").status_code in (401, 403)
