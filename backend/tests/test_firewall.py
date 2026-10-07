"""Tests: nft render pur (sans daemon) + validation FirewallRule."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import nft


def test_validate_ok():
    r = nft.validate_rule({"name": "web", "chain": "input", "action": "accept",
                           "proto": "tcp", "dport": 443})
    assert r["dport"] == 443


def test_validate_ko():
    for bad in [{"chain": "nope"}, {"action": "explode"}, {"proto": "all", "dport": 80},
                {"src": "999.1.1.1/99"}, {"action": "dnat", "chain": "input"},
                {"action": "masquerade", "chain": "input"}, {"dport": 99999}]:
        try:
            nft.validate_rule({"name": "t", **bad})
        except ValueError:
            continue
        raise AssertionError(f"{bad} aurait du etre refuse")


def test_render_full():
    rules = [
        {"name": "web", "chain": "input", "action": "accept", "proto": "tcp",
         "dport": 443, "position": 10, "enabled": True},
        {"name": "fwd", "chain": "forward", "action": "accept", "proto": "all",
         "src": "192.168.20.0/24", "out_if": "eth0", "position": 20, "enabled": True},
        {"name": "p80", "chain": "prerouting", "action": "dnat", "proto": "tcp",
         "dport": 80, "nat_to": "192.168.20.10:8080", "position": 30, "enabled": True},
        {"name": "masq", "chain": "postrouting", "action": "masquerade", "proto": "all",
         "src": "192.168.20.0/24", "out_if": "eth0", "position": 40, "enabled": True},
        {"name": "off", "chain": "input", "action": "drop", "proto": "all",
         "position": 50, "enabled": False},
    ]
    txt = nft.render(rules, input_policy="drop")
    assert "flush ruleset" in txt and "table inet filter" in txt and "table ip nat" in txt
    assert "tcp dport 443" in txt and "policy drop" in txt
    assert "dnat to 192.168.20.10:8080" in txt and "masquerade" in txt
    assert "off" not in txt  # desactivee exclue
