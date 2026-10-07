"""Tests API: DHCP, firewall, VPN, IPAM, reseau (RBAC + validation)."""
import os
import sys
from pathlib import Path

TMPDB = "/tmp/infraos-test-infra.db"
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


def test_dhcp_scope_flow(auth):
    with TestClient(app) as c:
        bad = {"name": "lan", "subnet": "not-a-net", "pool_start": "192.168.20.100",
               "pool_end": "192.168.20.200"}
        assert c.post("/api/v1/dhcp/scopes", json=bad, headers=auth).status_code == 400
        good = {**bad, "subnet": "192.168.20.0/24", "gateway": "192.168.20.254",
                "dns": ["192.168.20.254"], "domain": "lan"}
        r = c.post("/api/v1/dhcp/scopes", json=good, headers=auth)
        assert r.status_code == 200
        sid = r.json()["id"]
        assert c.post(f"/api/v1/dhcp/scopes/{sid}/reservations",
                      json={"mac": "bad", "ip": "192.168.20.50"}, headers=auth).status_code == 400
        r = c.post(f"/api/v1/dhcp/scopes/{sid}/reservations",
                   json={"mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.20.50",
                         "hostname": "srv"}, headers=auth)
        assert r.status_code == 200 and r.json()["mac"] == "aa:bb:cc:dd:ee:01"
        assert c.get("/api/v1/dhcp/leases", headers=auth).status_code == 200
        assert c.get("/api/v1/dhcp/scopes").status_code in (401, 403)


def test_firewall_preview(auth):
    with TestClient(app) as c:
        assert c.post("/api/v1/firewall/rules",
                      json={"name": "bad", "chain": "nope"}, headers=auth).status_code == 400
        assert c.post("/api/v1/firewall/rules",
                      json={"name": "web", "chain": "input", "action": "accept",
                            "proto": "tcp", "dport": 443}, headers=auth).status_code == 200
        r = c.get("/api/v1/firewall/preview", headers=auth)
        assert "tcp dport 443" in r.json()["ruleset"]


def test_ipam_flow(auth):
    with TestClient(app) as c:
        assert c.post("/api/v1/ipam/networks",
                      json={"name": "x", "cidr": "nope"}, headers=auth).status_code == 400
        r = c.post("/api/v1/ipam/networks",
                   json={"name": "lan", "cidr": "192.168.20.0/24",
                         "gateway": "192.168.20.254"}, headers=auth)
        nid = r.json()["id"]
        r = c.post(f"/api/v1/ipam/networks/{nid}/hosts", json={"hostname": "srv1"}, headers=auth)
        assert r.json()["ip"] == "192.168.20.1"
        r = c.get(f"/api/v1/ipam/networks/{nid}", headers=auth)
        assert r.json()["used"] == 2  # gateway reservee + srv1


def test_network_read_and_guards(auth):
    with TestClient(app) as c:
        assert c.get("/api/v1/network/routes", headers=auth).status_code == 200
        assert c.get("/api/v1/network/dns-resolver", headers=auth).status_code == 200
        assert c.post("/api/v1/network/static",
                      json={"interface": "eth0;rm", "cidr": "10.0.0.5/24"},
                      headers=auth).status_code == 400
        assert c.post("/api/v1/network/vlan",
                      json={"interface": "eth0", "vlan_id": 9999},
                      headers=auth).status_code == 400


def test_network_link_bridge_remove_guards(auth):
    with TestClient(app) as c:
        # link : nom d'interface dangereux refuse (validation avant exec)
        assert c.post("/api/v1/network/link",
                      json={"interface": "eth0;rm -rf /", "up": True},
                      headers=auth).status_code == 400
        # bridge : nom invalide refuse avant ecriture
        assert c.post("/api/v1/network/bridge",
                      json={"name": "br.test"}, headers=auth).status_code == 400
        assert c.post("/api/v1/network/bridge",
                      json={"name": "br0;reboot"}, headers=auth).status_code == 400
        # suppression : confirm requis, puis config inexistante = 400
        assert c.delete("/api/v1/network/interface/br7z9q", headers=auth).status_code == 400
        assert c.delete("/api/v1/network/interface/br7z9q?confirm=true",
                        headers=auth).status_code == 400
        # RBAC : sans token = refuse
        assert c.post("/api/v1/network/link",
                      json={"interface": "eth0", "up": True}).status_code in (401, 403)


def test_network_dhcp_and_staged_config(auth):
    with TestClient(app) as c:
        # dhcp : interface dangereuse refusee avant toute ecriture
        assert c.post("/api/v1/network/dhcp",
                      json={"interface": "eth0;rm"}, headers=auth).status_code == 400
        # config stagee : shape attendu (prefill UI statique/dhcp)
        r = c.get("/api/v1/network/config/eth0", headers=auth)
        assert r.status_code == 200
        j = r.json()
        assert {"interface", "exists", "method", "cidr", "gateway"} <= set(j)
        assert j["method"] in (None, "static", "dhcp")
        # config stagee : nom d'interface invalide refuse
        assert c.get("/api/v1/network/config/eth0;rm", headers=auth).status_code == 400
        # RBAC : sans token = refuse
        assert c.get("/api/v1/network/config/eth0").status_code in (401, 403)


def test_vpn_validation(auth):
    with TestClient(app) as c:
        assert c.post("/api/v1/vpn/servers",
                      json={"name": "eth0", "address": "10.8.0.1/24"},
                      headers=auth).status_code == 400
