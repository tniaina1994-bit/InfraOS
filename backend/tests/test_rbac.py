"""Tests: 4 roles, matrice, assignation, rate-limit, headers, /v1/health."""
import os
import sys
from pathlib import Path

TMPDB = "/tmp/infraos-test-rbac.db"
if os.path.exists(TMPDB):
    os.remove(TMPDB)
os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
os.environ["INFRAOS_ADMIN_PASSWORD"] = "Testpw123456"
os.environ["INFRAOS_JWT_SECRET"] = "test-secret-32-chars-minimum-xyz"
os.environ["INFRAOS_RATE_LOGIN_N"] = "1000"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "core"))

from infraos import db as dbmod


def _ensure():
    os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
    dbmod._engine = None
    dbmod._SessionFactory = None
    from infraos.db import init_db as _init, get_session as _sess
    from infraos.models import User as _User
    from infraos.security import hash_password as _hash
    _init(os.environ["INFRAOS_DB_URL"])
    _db = _sess()
    if not _db.query(_User).filter_by(username="admin").first():
        _db.add(_User(username="admin", password_hash=_hash("Testpw123456"), role="superadmin"))
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


def test_roles_matrix(auth):
    with TestClient(app) as c:
        r = c.get("/api/v1/roles", headers=auth)
        names = [x["name"] for x in r.json()["roles"]]
        assert names == ["superadmin", "admin", "operator", "readonly"]
        sa = [x for x in r.json()["roles"] if x["name"] == "superadmin"][0]
        assert "roles:manage" in sa["permissions"]
        ro = [x for x in r.json()["roles"] if x["name"] == "readonly"][0]
        assert "users:write" not in ro["permissions"]


def test_assign_revoke_cycle(auth):
    with TestClient(app) as c:
        c.post("/api/v1/users", json={"username": "op1", "password": "Op1-mot-de-passe-99",
                                      "role": "operator"}, headers=auth)
        r = c.post("/api/v1/roles/users/op1", json={"role": "admin"}, headers=auth)
        assert r.status_code == 200
        r = c.get("/api/v1/users", headers=auth)
        op1 = [u for u in r.json()["users"] if u["username"] == "op1"][0]
        assert op1["effective_role"] == "admin"
        assert c.delete("/api/v1/roles/users/op1/admin", headers=auth).status_code == 200


def test_admin_cannot_grant_admin():
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/login", json={"username": "admin", "password": "Testpw123456"})
        # admin est superadmin ici ; cree un admin intermediaire puis teste
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        c.post("/api/v1/users", json={"username": "mid", "password": "Mid-mot-de-passe-99",
                                      "role": "admin"}, headers=h)
        r2 = c.post("/api/v1/auth/login", json={"username": "mid", "password": "Mid-mot-de-passe-99"})
        hm = {"Authorization": f"Bearer {r2.json()['access_token']}"}
        r3 = c.post("/api/v1/users", json={"username": "x", "password": "X-mot-de-passe-99",
                                           "role": "admin"}, headers=hm)
        assert r3.status_code == 403


def test_rate_limit_blocks():
    import ratelimit
    os.environ["INFRAOS_RATE_LOGIN_N"] = "3"
    ratelimit.reset()
    try:
        with TestClient(app) as c:
            codes = [c.post("/api/v1/auth/login",
                            json={"username": "nobody", "password": "bad-password-1"}).status_code
                     for _ in range(5)]
            assert codes.count(429) >= 1
    finally:
        os.environ["INFRAOS_RATE_LOGIN_N"] = "1000"
        ratelimit.reset()


def test_secure_headers_and_v1_health(auth):
    with TestClient(app) as c:
        r = c.get("/api/v1/health", headers=auth)
        assert r.status_code == 200 and r.json()["status"] == "ok"
        assert r.headers.get("X-Frame-Options") == "DENY"
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
