"""Tests: monitoring (metriques, collect/history, agents)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import db as dbmod
from infraos import monitoring as mon


def _fresh():
    dbmod._engine = None
    dbmod._SessionFactory = None
    dbmod.init_db("sqlite:///:memory:")


def test_current_shape():
    m = mon.current()
    assert {"hostname", "cpu", "mem", "disk", "uptime", "processes"} <= set(m)


def test_collect_history():
    _fresh()
    mon.collect()
    h = mon.history()
    assert len(h) == 1 and "cpu" in h[0]


def test_agents():
    _fresh()
    mon.register_agent("pc1", "windows", "token-1234567890abcdef")
    assert mon.agents()[0]["hostname"] == "pc1"
    assert mon.agent_push("pc1", "token-1234567890abcdef", {"cpu": 10})["stored"] is True
    assert len(mon.history("pc1")) == 1
    try:
        mon.agent_push("pc1", "bad-token", {})
    except ValueError:
        pass
    else:
        raise AssertionError("token agent invalide aurait du lever")
    try:
        mon.register_agent("x", "amiga", "token-1234567890abcdef")
    except ValueError:
        return
    raise AssertionError("os agent invalide aurait du lever")
