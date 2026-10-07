"""Tests: config/service/health/event managers (sans mutation reelle)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import config_manager as cm
from infraos import service_manager as sm
from infraos import health_manager as hm
from infraos import event_manager as em


def test_config_show_redacted():
    d = cm.show()
    assert d.get("jwt_secret") == "***"
    assert "db_url" in d
    assert "@" not in d.get("db_url", "") or ":***@" in d["db_url"] or "sqlite" in d["db_url"]


def test_config_update_rejects_unknown():
    try:
        cm.update({"db_url": "x"}, actor="test")
    except ValueError as e:
        assert "non modifiables" in str(e)
        return
    raise AssertionError("cle interdite aurait du lever")


def test_config_update_rejects_bad_range():
    try:
        cm.update({"jwt_expire_min": 99999}, actor="test")
    except ValueError:
        return
    raise AssertionError("plage invalide aurait du lever")


def test_service_name_validation():
    for bad in ["ssh; rm -rf /", "../x", "", "ghost-service-xyz"]:
        try:
            sm.control(bad, "restart", actor="test")
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} aurait du etre refuse")


def test_service_bad_action():
    try:
        sm.control("ssh", "mask", actor="test")
    except ValueError:
        return
    raise AssertionError("mask aurait du etre refuse")


def test_health_shape():
    h = hm.check()
    assert h["status"] in ("ok", "degraded", "down")
    assert {"db", "cache", "disk", "memory", "services"} <= set(h["checks"])


def test_event_unknown_type():
    try:
        em.publish("rm -rf /", "test")
    except ValueError:
        return
    raise AssertionError("type inconnu aurait du lever")


def test_event_roundtrip_memory():
    em.publish("job.done", "test", "ping")
    evs = em.recent(5)
    assert any(e["type"] == "job.done" for e in evs)
