"""Tests: backends System/Identity/DNS/Network — jamais d'exception, allow-list."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos.modules import system as m_sys
from infraos.modules import identity as m_id
from infraos.modules import dns as m_dns
from infraos.modules import network as m_net


def test_system_status():
    st = m_sys.SystemModule().status()
    assert st.installed and "virt=" in st.detail


def test_identity_status():
    st = m_id.IdentityModule().status()
    assert st.installed and "utilisateurs" in st.detail


def test_dns_status_shape():
    st = m_dns.DnsModule().status()
    assert isinstance(st.installed, bool) and isinstance(st.running, bool)


def test_network_actions_closed():
    m = m_net.NetworkModule()
    assert set(m.actions()) == {"interfaces", "firewall", "ruleset"}
    try:
        m.run_action("reboot")
    except ValueError:
        return
    raise AssertionError("action inconnue aurait du lever")


def test_network_firewall():
    d = m_net.NetworkModule().run_action("firewall")
    assert "full_support" in d
