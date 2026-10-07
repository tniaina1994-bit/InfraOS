"""Tests: catalogue point 8 — les 17 modules futurs + system decouvrables et geres."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import module_manager as mm

# point 8 : manifest name -> titre attendu
CATALOG = {
    "identity": "Identité", "domain": "Domaine", "dns": "DNS",
    "dhcp": "DHCP", "network": "Réseau", "firewall": "Firewall",
    "vpn": "VPN", "ipam": "IPAM", "discovery": "Network Discovery",
    "monitoring": "Monitoring", "fileshare": "fichiers", "backup": "Sauvegardes",
    "security": "Security", "loganalyzer": "Log Analyzer",
    "virtualization": "Virtualization", "updates": "Mises à jour",
    "certificates": "Certificate", "system": "Système",
}


def test_catalog_discoverable():
    names = {m["name"] for m in mm.discover()}
    missing = [n for n in CATALOG if n not in names]
    assert not missing, f"modules manquants: {missing}"


def test_catalog_managed():
    unmanaged = []
    for name in CATALOG:
        try:
            st = mm.status(name)
            if not st.get("managed"):
                unmanaged.append(name)
        except Exception as e:
            unmanaged.append(f"{name}({e})")
    assert not unmanaged, f"backends manquants: {unmanaged}"


def test_catalog_status_never_raises():
    for name in CATALOG:
        st = mm.status(name)
        assert {"installed", "running", "version", "services"} <= set(st)


def test_catalog_planned_actions_do_not_execute():
    be = mm._backend("dhcp")
    r = be.run_action("scopes")
    assert r.get("status") == "planned"
    be2 = mm._backend("certificates")
    inv = be2.run_action("inventory")
    assert "certificates" in inv
