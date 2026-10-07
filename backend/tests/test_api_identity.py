"""Tests API: groups, politique mdp, sessions/logout, permissions, domain."""
import os
import sys
from pathlib import Path

TMPDB = "/tmp/infraos-test-identity.db"
if os.path.exists(TMPDB):
    os.remove(TMPDB)
os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
os.environ["INFRAOS_ADMIN_PASSWORD"] = "Testpw123456"
os.environ["INFRAOS_JWT_SECRET"] = "test-secret-32-chars-minimum-xyz"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "core"))

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
    # portee fonction : chaque test a son token (logout d'un test n'affecte pas les autres)
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/login", json={"username": "admin", "password": "Testpw123456"})
        assert r.status_code == 200
        return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_password_policy_enforced(auth):
    with TestClient(app) as c:
        r = c.post("/api/v1/users", json={"username": "weak", "password": "x", "role": "viewer"}, headers=auth)
        assert r.status_code == 400
        r = c.post("/api/v1/users", json={"username": "alice", "password": "Alice-mot-de-passe-42",
                                          "role": "viewer"}, headers=auth)
        assert r.status_code == 200


def test_groups_and_effective_role(auth):
    with TestClient(app) as c:
        assert c.post("/api/v1/groups", json={"name": "ops", "role": "operator"}, headers=auth).status_code == 200
        r = c.post("/api/v1/groups/ops/members", json={"username": "alice"}, headers=auth)
        assert r.status_code == 200 and r.json()["effective_role"] == "operator"
        r = c.get("/api/v1/users", headers=auth)
        alice = [u for u in r.json()["users"] if u["username"] == "alice"][0]
        assert alice["effective_role"] == "operator" and "ops" in alice["groups"]


def test_self_password_and_sessions(auth):
    with TestClient(app) as c:
        r = c.get("/api/v1/auth/sessions", headers=auth)
        assert r.status_code == 200 and len(r.json()["sessions"]) >= 1
        # changement avec mauvais actuel refuse
        r = c.post("/api/v1/users/me/password",
                   json={"current_password": "bad", "new_password": "Nouveau-mot-de-passe-99"}, headers=auth)
        assert r.status_code == 401
        # logout revoque : token inutilisable ensuite
        assert c.post("/api/v1/auth/logout", headers=auth).status_code == 200
        assert c.get("/api/v1/auth/me", headers=auth).status_code == 401


def test_permissions_endpoint():
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/login", json={"username": "admin", "password": "Testpw123456"})
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = c.get("/api/v1/users/me/permissions", headers=h)
        assert r.status_code == 200 and "services:control" in r.json()["permissions"]


def test_domain_readiness(auth):
    with TestClient(app) as c:
        r = c.get("/api/v1/domain/readiness", headers=auth)
        assert r.status_code == 200
        body = r.json()
        assert {"ready", "provisioned", "checks", "strategy"} <= set(body)
        assert c.get("/api/v1/domain/readiness").status_code in (401, 403)
