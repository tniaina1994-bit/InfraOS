"""Tests: WireGuard validation + rendu conf (sans daemon)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import wireguard as wg

PUB = "A" * 43 + "="


def test_server_ok():
    assert wg.validate_server("wg0", "10.8.0.1/24", 51820)["port"] == 51820
    for bad in [("eth0", "10.8.0.1/24", 51820), ("wg0", "nope", 51820),
                ("wg0", "10.8.0.1/24", 99999), ("wg99x", "10.8.0.1/24", 51820)]:
        try:
            wg.validate_server(*bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} aurait du etre refuse")


def test_peer_ok_ko():
    assert wg.validate_peer("laptop", PUB, "10.8.0.2/32")["allowed_ips"] == "10.8.0.2/32"
    for bad in [("x", "badkey", "10.8.0.2/32"), ("x", PUB, ""),
                ("x", PUB, "999.1.1.1/99"), ("x", PUB, "10.8.0.2/32", "host-no-port")]:
        try:
            wg.validate_peer(*bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} aurait du etre refuse")


def test_render_conf():
    srv = {"name": "wg0", "address": "10.8.0.1/24", "port": 51820, "private_key": "PRIV"}
    peers = [{"name": "laptop", "public_key": PUB, "preshared_key": "",
              "allowed_ips": "10.8.0.2/32", "endpoint": "1.2.3.4:51820", "keepalive": 25}]
    txt = wg.render_conf(srv, peers)
    assert "[Interface]" in txt and "PrivateKey = PRIV" in txt
    assert f"PublicKey = {PUB}" in txt and "Endpoint = 1.2.3.4:51820" in txt
