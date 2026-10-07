"""Tests API: DNS CRUD + validation + RBAC (apply teste sur LXC avec BIND9)."""
import os
import sys
from pathlib import Path

TMPDB = "/tmp/infraos-test-dns.db"
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


@pytest.fixture()
def auth():
    _ensure()
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/login", json={"username": "admin", "password": "Testpw123456"})
        assert r.status_code == 200
        return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _isolated():
    _ensure()
    yield


def test_zones_crud(auth):
    with TestClient(app) as c:
        assert c.post("/api/v1/dns/zones", json={"name": "lan.local"}, headers=auth).status_code == 200
        assert c.post("/api/v1/dns/zones", json={"name": "lan.local"}, headers=auth).status_code == 409
        assert c.post("/api/v1/dns/zones", json={"name": "bad zone!"}, headers=auth).status_code == 400
        r = c.post("/api/v1/dns/zones", json={"name": "10.in-addr.arpa", "reverse": True}, headers=auth)
        assert r.status_code == 200
        r = c.get("/api/v1/dns/zones", headers=auth)
        assert {z["name"] for z in r.json()["zones"]} >= {"lan.local", "10.in-addr.arpa"}
        assert c.get("/api/v1/dns/zones").status_code in (401, 403)


def test_records_crud_and_cname(auth):
    with TestClient(app) as c:
        c.post("/api/v1/dns/zones", json={"name": "t.local"}, headers=auth)
        assert c.post("/api/v1/dns/zones/t.local/records",
                      json={"name": "www", "rtype": "A", "value": "10.0.0.1"}, headers=auth).status_code == 200
        assert c.post("/api/v1/dns/zones/t.local/records",
                      json={"name": "bad", "rtype": "A", "value": "999.1.1.1"}, headers=auth).status_code == 400
        assert c.post("/api/v1/dns/zones/t.local/records",
                      json={"name": "www", "rtype": "CNAME", "value": "x.t.local"}, headers=auth).status_code == 400
        r = c.post("/api/v1/dns/zones/t.local/records",
                   json={"name": "mail", "rtype": "MX", "value": "m.t.local", "priority": 5}, headers=auth)
        rid = r.json()["id"]
        assert c.delete(f"/api/v1/dns/records/{rid}", headers=auth).status_code == 200


def test_forward_zone_and_servers(auth):
    with TestClient(app) as c:
        r = c.post("/api/v1/dns/zones", json={"name": "corp", "kind": "forward",
                                              "forwarders": ["10.0.0.53"]}, headers=auth)
        assert r.status_code == 200
        assert c.post("/api/v1/dns/zones/corp/records",
                      json={"name": "x", "rtype": "A", "value": "10.0.0.1"}, headers=auth).status_code == 400
        assert c.put("/api/v1/dns/servers", json={"forwarders": ["not-an-ip"]}, headers=auth).status_code == 400
