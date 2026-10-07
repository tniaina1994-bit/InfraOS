"""Tests: rendu BIND9 pur (sans daemon)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import dns_render as rnd


def test_render_zone():
    zone = {"name": "lan.local", "ttl": 3600}
    recs = [{"name": "@", "rtype": "NS", "value": "ns1.lan.local", "priority": 0, "ttl": 0},
            {"name": "www", "rtype": "A", "value": "192.168.10.10", "priority": 0, "ttl": 0},
            {"name": "@", "rtype": "MX", "value": "mail.lan.local", "priority": 10, "ttl": 0},
            {"name": "@", "rtype": "TXT", "value": "v=spf1 ~all", "priority": 0, "ttl": 0}]
    txt = rnd.render_zone(zone, recs, 2026010101)
    assert "$ORIGIN lan.local." in txt and "SOA" in txt and "2026010101" in txt
    assert "www IN A 192.168.10.10" in txt
    assert "IN MX 10 mail.lan.local." in txt
    assert 'IN TXT "v=spf1 ~all"' in txt


def test_render_named_conf():
    zones = [{"name": "lan.local", "kind": "master", "enabled": True},
             {"name": "ext", "kind": "forward", "enabled": True, "forwarders": '["1.1.1.1"]'},
             {"name": "old", "kind": "master", "enabled": False}]
    txt = rnd.render_named_conf(zones, ["192.168.10.252"], {})
    assert 'zone "lan.local"' in txt and 'file "/etc/bind/infraos/db.lan.local"' in txt
    assert 'type forward' in txt and '1.1.1.1;' in txt
    assert 'zone "old"' not in txt
    assert 'forwarders { 192.168.10.252; }' in txt


def test_serial_monotonic():
    assert rnd.serial_now(9999999999) == 10000000000
    assert rnd.serial_now(0) >= 2020010100
