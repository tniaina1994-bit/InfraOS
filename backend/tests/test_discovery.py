"""Tests: discovery (validation, parse XML, comparaison)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import discovery as disc

XML = """<?xml version="1.0"?>
<nmaprun><host><status state="up"/>
<address addr="192.168.10.50" addrtype="ipv4"/>
<address addr="BC:24:11:E7:EA:83" addrtype="mac"/>
<hostnames><hostname name="srv.lan"/></hostnames>
<ports><port protocol="tcp" portid="22"><state state="open"/><service name="ssh"/></port>
<port protocol="tcp" portid="80"><state state="closed"/></port></ports>
<os><osmatch name="Linux 5.X"/></os></host>
<host><status state="down"/><address addr="192.168.10.51" addrtype="ipv4"/></host>
</nmaprun>"""


def test_validate_guards():
    disc.validate_target("192.168.10.0/24", "ping")
    disc.validate_target("192.168.10.50", "os")
    for bad in ["0.0.0.0/0", "10.0.0.0/8", "nope", ""]:
        try:
            disc.validate_target(bad, "ping")
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} aurait du etre refuse")
    try:
        disc.validate_target("192.168.10.0/24", "nuke")
    except ValueError:
        return
    raise AssertionError("profil inconnu aurait du lever")


def test_parse_xml():
    hosts = disc.parse_xml(XML)
    assert len(hosts) == 1
    h = hosts[0]
    assert h["ip"] == "192.168.10.50" and h["mac"] == "bc:24:11:e7:ea:83"
    assert h["hostname"] == "srv.lan" and h["os"] == "Linux 5.X"
    assert h["ports"] == [{"port": 22, "proto": "tcp", "service": "ssh"}]


def test_compare():
    old = [{"ip": "a", "mac": "m"}, {"ip": "b", "mac": "m"}]
    new = [{"ip": "b", "mac": "m2"}, {"ip": "c", "mac": "m"}]
    d = disc.compare(old, new)
    assert d == {"new": ["c"], "gone": ["a"], "changed": ["b"]}


def test_arp_tolerant():
    assert isinstance(disc.arp_table(), list)
