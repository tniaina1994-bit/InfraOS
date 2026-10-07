"""Tests: domain readiness (lecture seule, sans provision)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import domain as dom


def test_readiness_shape():
    r = dom.readiness()
    assert {"ready", "provisioned", "checks", "strategy"} <= set(r)
    assert isinstance(r["provisioned"], bool)
    names = [c["check"] for c in r["checks"]]
    assert {"hyperviseur", "paquets", "ports", "provision"} <= set(names)
