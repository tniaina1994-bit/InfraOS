"""Tests: validation DNS (types, zones, CNAME exclusif)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import dns_validate as dv


def test_zone_names():
    assert dv.zone_name("Lan.Local", False) == "lan.local"
    assert dv.zone_name("10.in-addr.arpa", True) == "10.in-addr.arpa"
    for bad, rev in [("10.in-addr.arpa", False), ("lan.local", True), ("", False), ("a" * 300, False)]:
        try:
            dv.zone_name(bad, rev)
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} aurait du etre refuse")


def test_records_ok():
    assert dv.record("A", "www", "192.168.10.10")["rtype"] == "A"
    assert dv.record("aaaa", "h", "::1")["rtype"] == "AAAA"
    assert dv.record("MX", "@", "mail.lan.local", 10)["priority"] == 10
    assert dv.record("TXT", "@", "v=spf1 ~all")["value"] == "v=spf1 ~all"
    assert dv.record("PTR", "10", "srv.lan.local")["rtype"] == "PTR"


def test_records_ko():
    for args in [("A", "www", "999.1.1.1"), ("AAAA", "h", "zzz"),
                 ("MX", "@", "mail", 99999), ("PTR", "www", "srv.lan.local"),
                 ("SOA", "@", "x"), ("A", "bad name!", "1.2.3.4")]:
        try:
            dv.record(*args)
        except ValueError:
            continue
        raise AssertionError(f"{args} aurait du etre refuse")


def test_cname_exclusive():
    existing = [{"id": 1, "name": "www", "rtype": "A"}]
    dv.check_cname_exclusive(existing, {"name": "mail", "rtype": "CNAME"})
    try:
        dv.check_cname_exclusive(existing, {"name": "www", "rtype": "CNAME"})
    except ValueError:
        return
    raise AssertionError("CNAME sur A aurait du lever")
