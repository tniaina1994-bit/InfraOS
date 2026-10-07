"""Tests: audit tuple + security center + config structure."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import db as dbmod
from infraos import event_manager as em
from infraos import security_center as sc
from infraos import config_manager as cm


def _fresh():
    dbmod._engine = None
    dbmod._SessionFactory = None
    dbmod.init_db("sqlite:///:memory:")


def test_audit_tuple_fields():
    _fresh()
    em.publish("user.login", "admin", "role=admin", resource="auth/login",
               ip="192.168.20.10", result="SUCCESS")
    em.publish("user.login", "bob", "bad", resource="auth/login",
               ip="192.168.20.11", result="FAILURE")
    evs = em.recent(5)
    login = [e for e in evs if e["type"] == "user.login"]
    bob = [e for e in login if e["actor"] == "bob"][0]
    assert bob["ip"] == "192.168.20.11" and bob["result"] == "FAILURE"
    assert bob["resource"] == "auth/login"
    assert sc.failed_logins(24, 10)[0]["ip"] == "192.168.20.11"


def test_suspicious_bruteforce():
    _fresh()
    for _ in range(5):
        em.publish("user.login", "x", "bad", resource="auth/login",
                   ip="10.9.9.9", result="FAILURE")
    rules = [s["rule"] for s in sc.suspicious(24)]
    assert "bruteforce" in rules


def test_overview_shape():
    _fresh()
    o = sc.overview()
    assert {"failed_logins_24h", "suspicious", "updates_pending", "integrations"} <= set(o)
    assert {"journald", "rsyslog", "suricata", "fail2ban"} == {i["name"] for i in o["integrations"]}


def test_config_structure_tmp(tmp_path):
    base = tmp_path / "etc"
    out = cm.ensure_structure(base)
    assert (base / "secrets").exists()
    assert out["base"] == str(base)
    r = cm.set_secret("api-key", "s3cret", base)
    assert r["stored"] is True
    p = base / "secrets" / "api-key"
    assert p.read_text() == "s3cret"
    import os
    if os.name == "posix":  # permissions POSIX : verifiees sur LXC/Debian
        assert oct(os.stat(p).st_mode & 0o777) == "0o600"
    m = cm.module_config("dns", {"a": 1}, base)
    assert m["config"] == {"a": 1}
    assert cm.module_config("dns", base=base)["config"] == {"a": 1}
    try:
        cm.module_config("dns", {"bad key!": 1}, base)
    except ValueError:
        pass
    else:
        raise AssertionError("cle module invalide aurait du lever")
    try:
        cm.set_secret("../evil", "x", base)
    except ValueError:
        pass
    else:
        raise AssertionError("secret invalide aurait du lever")
