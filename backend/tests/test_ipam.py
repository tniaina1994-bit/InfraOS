"""Tests: IPAM validation + allocation (sqlite memoire)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import db as dbmod
from infraos.models import IpamNetwork, IpamHost
from infraos import ipam as ipam_mod


def _fresh():
    dbmod._engine = None
    dbmod._SessionFactory = None
    dbmod.init_db("sqlite:///:memory:")
    s = dbmod.get_session()
    s.add(IpamNetwork(name="lan", cidr="192.168.20.0/24", gateway="192.168.20.254"))
    s.commit()
    nid = s.query(IpamNetwork).first().id
    s.close()
    return nid


def test_allocate_skips_network_gateway():
    nid = _fresh()
    a = ipam_mod.allocate(nid, hostname="srv1")
    assert a["ip"] == "192.168.20.1"
    s = dbmod.get_session()
    s.add(IpamHost(network_id=nid, ip="192.168.20.2", hostname="x"))
    s.commit()
    s.close()
    b = ipam_mod.allocate(nid, hostname="srv2")
    assert b["ip"] == "192.168.20.3"


def test_usage_and_bad_mac():
    nid = _fresh()
    u = ipam_mod.usage(nid)
    assert u["total"] == 254 and u["used"] == 0 and u["free"] == 254
    try:
        ipam_mod.allocate(nid, mac="bad-mac")
    except ValueError:
        return
    raise AssertionError("MAC invalide aurait du lever")


def test_validate_network():
    ipam_mod.validate_network("192.168.20.0/24", "192.168.20.254", 20)
    try:
        ipam_mod.validate_network("not-a-net")
    except ValueError:
        return
    raise AssertionError("CIDR invalide aurait du lever")
