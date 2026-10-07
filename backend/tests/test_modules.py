"""Tests API: modules via Module Manager (RBAC, lifecycle, actions fermees)."""
import os
import sys
from pathlib import Path

TMPDB = "/tmp/infraos-test-modules.db"
if os.path.exists(TMPDB):
    os.remove(TMPDB)
os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
os.environ["INFRAOS_ADMIN_PASSWORD"] = "testpw123"
os.environ["INFRAOS_JWT_SECRET"] = "test-secret-32-chars-minimum-xyz"
os.environ["INFRAOS_DATA_DIR"] = "/tmp/infraos-test-modstate"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "core"))

from infraos import db as dbmod
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

import pytest

from fastapi.testclient import TestClient
from main import app


def _ensure():
    os.environ["INFRAOS_RATE_LOGIN_N"] = "1000"
    try:
        from ratelimit import reset as _rlreset
        _rlreset()
    except Exception:
        pass
    os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
    os.environ["INFRAOS_DATA_DIR"] = "/tmp/infraos-test-modstate"
    dbmod._engine = None
    dbmod._SessionFactory = None
    _init(os.environ["INFRAOS_DB_URL"])
    _db = _sess()
    if not _db.query(_User).filter_by(username="admin").first():
        _db.add(_User(username="admin", password_hash=_hash("testpw123"), role="admin"))
        _db.commit()
    _db.close()


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


def test_list_requires_auth():
    with TestClient(app) as c:
        assert c.get("/api/v1/modules").status_code in (401, 403)


def test_list_has_core_four(auth):
    with TestClient(app) as c:
        r = c.get("/api/v1/modules", headers=auth)
        assert r.status_code == 200
        names = {m["name"] for m in r.json()["modules"]}
        assert {"system", "identity", "dns", "network"} <= names


def test_detail_and_order(auth):
    with TestClient(app) as c:
        r = c.get("/api/v1/modules/dns", headers=auth)
        assert r.status_code == 200 and r.json()["name"] == "dns"
        order = c.get("/api/v1/modules", headers=auth).json()["order"]
        assert order.index("network") < order.index("dns")


def test_enable_disable_cycle(auth):
    with TestClient(app) as c:
        # dns est requis par domain (actif par defaut) : le garde-fou refuse
        r = c.post("/api/v1/modules/dns/disable", headers=auth)
        assert r.status_code == 400 and "requis par" in r.text
        assert c.post("/api/v1/modules/domain/disable", headers=auth).status_code == 200
        assert c.post("/api/v1/modules/dns/disable", headers=auth).status_code == 200
        d = c.get("/api/v1/modules/dns", headers=auth).json()
        assert d["enabled"] is False
        assert c.post("/api/v1/modules/dns/enable", headers=auth).status_code == 200
        assert c.post("/api/v1/modules/domain/enable", headers=auth).status_code == 200


def test_unknown_action_rejected(auth):
    with TestClient(app) as c:
        r = c.post("/api/v1/modules/dns/action",
                   json={"action": "rm -rf /", "params": {}}, headers=auth)
        assert r.status_code == 400


def test_dependencies_endpoint(auth):
    with TestClient(app) as c:
        r = c.get("/api/v1/modules/dns/dependencies", headers=auth)
        assert r.status_code == 200
        body = r.json()
        assert body["satisfied"] is True
        assert body["dependencies"][0]["name"] == "network"
        assert c.get("/api/v1/modules/ghost/dependencies", headers=auth).status_code == 404


def test_uninstall_guards(auth):
    with TestClient(app) as c:
        # network protege (dependants actifs)
        assert c.post("/api/v1/modules/network/uninstall", headers=auth).status_code == 400
        # sans token refuse
        assert c.post("/api/v1/modules/identity/uninstall").status_code in (401, 403)


def test_network_action(auth):
    with TestClient(app) as c:
        r = c.post("/api/v1/modules/network/action",
                   json={"action": "firewall", "params": {}}, headers=auth)
        assert r.status_code == 200 and "full_support" in r.json()
