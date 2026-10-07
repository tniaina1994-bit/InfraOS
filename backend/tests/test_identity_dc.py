"""Tests API — Identity & Domain Controller (§6-17) sans samba provisionne.

Le dev machine (Windows) n'a ni samba ni sam.ldb : on verifie le comportement
gracieux (listes vides, 400 "domaine non provisionne"), le RBAC (operator/admin),
les validateurs d'entrees et les gardes exec (allow-list + $ suffixe).
"""
import os
import sys
from pathlib import Path

TMPDB = "/tmp/infraos-test-identity-dc.db"
if os.path.exists(TMPDB):
    os.remove(TMPDB)
os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
os.environ["INFRAOS_ADMIN_PASSWORD"] = "Testpw123456"
os.environ["INFRAOS_JWT_SECRET"] = "test-secret-32-chars-minimum-xyz"
os.environ["INFRAOS_RATE_LOGIN_N"] = "1000"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "core"))

from infraos import db as dbmod


def _ensure():
    os.environ["INFRAOS_DB_URL"] = f"sqlite:///{TMPDB}"
    dbmod._engine = None
    dbmod._SessionFactory = None
    from infraos.db import get_session as _sess
    from infraos.db import init_db as _init
    from infraos.models import User as _User
    from infraos.security import hash_password as _hash
    _init(os.environ["INFRAOS_DB_URL"])
    db = _sess()
    if not db.query(_User).filter_by(username="admin").first():
        db.add(_User(username="admin", password_hash=_hash("Testpw123456"),
                     role="admin"))
    if not db.query(_User).filter_by(username="viewer").first():
        db.add(_User(username="viewer", password_hash=_hash("Testpw123456"),
                     role="viewer"))
    db.commit()
    db.close()


_ensure()

import pytest
from fastapi.testclient import TestClient
from main import app

API = "/api/v1/identity"


@pytest.fixture(autouse=True)
def _isolated():
    _ensure()
    yield


@pytest.fixture()
def auth():
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/login",
                   json={"username": "admin", "password": "Testpw123456"})
        assert r.status_code == 200
        return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def viewer():
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/login",
                   json={"username": "viewer", "password": "Testpw123456"})
        assert r.status_code == 200
        return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_status_unprovisioned(auth):
    with TestClient(app) as c:
        r = c.get(f"{API}/status", headers=auth)
        assert r.status_code == 200
        body = r.json()
        assert body["provisioned"] is False
        assert body["status"] in ("unconfigured", "healthy", "degraded")


def test_health_warning_when_no_domain(auth):
    with TestClient(app) as c:
        r = c.get(f"{API}/health", headers=auth)
        assert r.status_code == 200
        body = r.json()
        assert body["overall"] in ("WARNING", "ERROR", "PASS")
        names = [ch["check"] for ch in body["checks"]]
        assert "hostname" in names and "fqdn" in names
        # non provisionne : pas de check DNS/Kerberos qui echouerait en erreur
        assert any(ch["status"] == "WARNING" for ch in body["checks"])


def test_domain_info_graceful(auth):
    with TestClient(app) as c:
        r = c.get(f"{API}/domain", headers=auth)
        assert r.status_code == 200
        assert r.json()["provisioned"] is False


@pytest.mark.parametrize("path", ["/users", "/groups", "/ous", "/computers"])
def test_lists_graceful_when_no_domain(auth, path):
    with TestClient(app) as c:
        r = c.get(f"{API}{path}", headers=auth)
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 0
        assert "provisionne" in body.get("detail", "")


def test_policies_graceful(auth):
    with TestClient(app) as c:
        r = c.get(f"{API}/policies", headers=auth)
        assert r.status_code == 200
        assert r.json()["settings"] == {}


@pytest.mark.parametrize("method,path,payload", [
    ("post", "/users", {"username": "alice", "password": "Str0ngPass!2026"}),
    ("post", "/groups", {"name": "IT"}),
    ("post", "/ous", {"name": "Utilisateurs"}),
    ("post", "/computers", {"name": "WS01"}),
    ("put", "/policies", {"min_pwd_length": 12}),
])
def test_mutations_require_provisioned(auth, method, path, payload):
    with TestClient(app) as c:
        fn = getattr(c, method)
        r = fn(f"{API}{path}", json=payload, headers=auth)
        assert r.status_code == 400
        assert "provisionne" in r.json()["detail"] or "domaine" in r.json()["detail"].lower()


def test_kerberos_test_requires_domain(auth):
    with TestClient(app) as c:
        r = c.post(f"{API}/test/kerberos",
                   json={"username": "Administrator", "password": "x" * 20},
                   headers=auth)
        assert r.status_code == 400


def test_domain_setup_validation(auth):
    with TestClient(app) as c:
        # realm invalide -> 400 avant toute action systeme
        r = c.post(f"{API}/domain/setup",
                   json={"domain": "pas-un-realm", "netbios": "CORP",
                         "hostname": "dc1", "ip": "192.168.1.10",
                         "admin_password": "Str0ngPass!2026", "confirm": True},
                   headers=auth)
        assert r.status_code == 400
        # IP invalide -> 400
        r = c.post(f"{API}/domain/setup",
                   json={"domain": "corp.example.internal", "netbios": "CORP",
                         "hostname": "dc1", "ip": "999.1.1.1",
                         "admin_password": "Str0ngPass!2026", "confirm": True},
                   headers=auth)
        assert r.status_code == 400


def test_preflight_endpoint(auth):
    with TestClient(app) as c:
        r = c.get(f"{API}/domain/preflight",
                  params={"domain": "corp.example.internal", "netbios": "CORP",
                          "hostname": "dc1", "ip": "192.168.1.39"},
                  headers=auth)
        assert r.status_code == 200
        body = r.json()
        assert "checks" in body or "preflight" in body or "ok" in body


def test_rbac_read_needs_operator(auth, viewer):
    with TestClient(app) as c:
        r = c.get(f"{API}/users", headers=viewer)
        assert r.status_code == 403


def test_rbac_write_needs_admin(viewer):
    with TestClient(app) as c:
        r = c.post(f"{API}/users",
                   json={"username": "bob", "password": "Str0ngPass!2026"},
                   headers=viewer)
        assert r.status_code == 403


def test_audit_identity_filter(auth):
    with TestClient(app) as c:
        r = c.get(f"{API}/audit", params={"limit": 10}, headers=auth)
        assert r.status_code == 200
        body = r.json()
        assert "events" in body
        for ev in body["events"]:
            assert ev["action"].startswith("identity.")


def test_join_info_graceful(auth):
    with TestClient(app) as c:
        r = c.get(f"{API}/domain/join", headers=auth)
        assert r.status_code == 200
        assert r.json()["provisioned"] is False


# ------------------------------------------------------------- unitaires ---

def test_validate_inputs_ok():
    from infraos.identity_domain import validate_inputs
    v = validate_inputs("corp.example.internal", "CORP", "dc1.lab", "192.168.1.39")
    assert v["domain"] == "corp.example.internal"
    assert v["netbios"] == "CORP"
    assert v["hostname"] == "dc1"
    assert v["fqdn"] == "dc1.corp.example.internal"


@pytest.mark.parametrize("domain,nb,host,ip", [
    ("no-dots", "CORP", "dc1", "192.168.1.1"),
    ("corp.example.internal", "TOO_LONG_NETBIOS_NAME", "dc1", "192.168.1.1"),
    ("corp.example.internal", "CORP", "bad_host", "192.168.1.1"),
    ("corp.example.internal", "CORP", "dc1", "999.1.1.1"),
    ("corp.example.internal", "CORP", "dc1", "not-an-ip"),
])
def test_validate_inputs_rejects(domain, nb, host, ip):
    from infraos.identity_domain import validate_inputs
    with pytest.raises(ValueError):
        validate_inputs(domain, nb, host, ip)


def test_samba_guards_without_domain():
    from infraos import identity_samba as sm
    with pytest.raises(ValueError, match="provisionne"):
        sm.get_user("alice")
    with pytest.raises(ValueError, match="provisionne"):
        sm.create_user({"username": "alice", "password": "Str0ngPass!2026"})
    with pytest.raises(ValueError, match="provisionne"):
        sm.set_password("alice", "Str0ngPass!2026")
    with pytest.raises(ValueError, match="provisionne"):
        sm.delete_group("IT")


def test_name_validation():
    from infraos import identity_samba as sm
    for bad in ("a;rm -rf", "a b", "x$(id)", "$(whoami)", "a|b", ""):
        with pytest.raises(ValueError):
            sm._acc(bad)


def test_group_name_allows_spaces():
    from infraos import identity_samba as sm
    assert sm._acc("Lab Admins", "groupe") == "Lab Admins"
    assert sm._acc("Domain Admins", "groupe") == "Domain Admins"
    for bad in ("a;rm", "a\nb", "", "bad!name", "a|b"):
        with pytest.raises(ValueError):
            sm._acc(bad, "groupe")
    # les comptes utilisateur restent stricts (pas d'espace)
    with pytest.raises(ValueError):
        sm._acc("lab user", "utilisateur")


def test_password_validation():
    from infraos import identity_samba as sm
    with pytest.raises(ValueError):
        sm._pw("court")
    with pytest.raises(ValueError):
        sm._pw("avec\nretour")
    assert sm._pw("Str0ngPass!2026") == "Str0ngPass!2026"


def test_exec_trailing_dollar_allowed_mid_dollar_rejected():
    """$ admis en suffixe (principal machine WS01$), refuse ailleurs."""
    from infraos.exec import ForbiddenCommand, run
    # suffixe : passe la validation (binaire absent -> rc 127, pas d'exception)
    r = run("samba-tool", "user", "enable", "WS01$", caller="test")
    assert r.rc == 127  # introuvable sur Windows
    with pytest.raises(ForbiddenCommand):
        run("samba-tool", "user", "enable", "WS$(id)")


def test_exec_still_blocks_shell_meta():
    from infraos.exec import ForbiddenCommand, run
    for arg in ("a;b", "a&&b", "a|b", "a`id`", "a\nb"):
        with pytest.raises(ForbiddenCommand):
            run("samba-tool", "user", "list", arg)


def test_uninstall_guard_blocks_without_confirm():
    from infraos.identity_domain import uninstall_guard
    out = uninstall_guard(False, actor="test")
    # non provisionne sur dev : garde retourne standard
    assert out["provisioned"] is False or out.get("status") == "blocked"


def test_domain_uninstall_endpoint(auth):
    with TestClient(app) as c:
        r = c.delete(f"{API}/domain", params={"confirm": "false"}, headers=auth)
        assert r.status_code == 200
        body = r.json()
        assert body["provisioned"] is False or body.get("status") == "blocked"
