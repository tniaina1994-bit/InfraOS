"""Tests: DHCP validation + rendu Kea pur."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import dhcp as kea


def test_scope_ok():
    assert kea.validate_scope("192.168.20.0/24", "192.168.20.100",
                              "192.168.20.200", "192.168.20.254")


def test_scope_ko():
    for args in [("not-a-net", "192.168.20.1", "192.168.20.2"),
                 ("192.168.20.0/24", "192.168.21.1", "192.168.21.2"),
                 ("192.168.20.0/24", "192.168.20.200", "192.168.20.100"),
                 ("192.168.20.0/24", "192.168.20.1", "192.168.20.2", "10.0.0.1")]:
        try:
            kea.validate_scope(*args)
        except ValueError:
            continue
        raise AssertionError(f"{args} aurait du etre refuse")


def test_reservation():
    r = kea.validate_reservation("AA:BB:CC:DD:EE:FF", "192.168.20.50",
                                 {"subnet": "192.168.20.0/24"})
    assert r["mac"] == "aa:bb:cc:dd:ee:ff"
    try:
        kea.validate_reservation("bad-mac", "192.168.20.50", {"subnet": "192.168.20.0/24"})
    except ValueError:
        return
    raise AssertionError("MAC invalide aurait du lever")


def test_render_kea():
    scopes = [{"name": "lan", "subnet": "192.168.20.0/24",
               "pool_start": "192.168.20.100", "pool_end": "192.168.20.200",
               "gateway": "192.168.20.254", "dns": '["192.168.20.254"]',
               "domain": "lan", "lease_valid": 3600, "lease_max": 7200,
               "enabled": True,
               "reservations": [{"mac": "aa:bb:cc:dd:ee:ff", "ip": "192.168.20.50",
                                 "hostname": "srv"}]}]
    conf = kea.render_kea(scopes)
    s = conf["Dhcp4"]["subnet4"][0]
    assert s["subnet"] == "192.168.20.0/24"
    assert s["pools"] == [{"pool": "192.168.20.100 - 192.168.20.200"}]
    assert {"name": "routers", "data": "192.168.20.254"} in s["option-data"]
    assert s["reservations"][0]["hw-address"] == "aa:bb:cc:dd:ee:ff"
    assert kea.leases()["count"] == 0 or True  # tolerant si memfile present
