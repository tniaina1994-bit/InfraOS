# SPDX-License-Identifier: GPL-3.0-or-later
"""VPN WireGuard — serveurs/peers (DB) -> wgX.conf + cles + wg-quick.

Cles generees cote serveur (`wg genkey`, allow-list), jamais transmises en
clair hors API TLS. OpenVPN : prevu (docs/VPN.md), non implemente.
"""
from __future__ import annotations
import ipaddress
import re
from pathlib import Path
from .exec import run

WG_DIR = Path("/etc/wireguard")
_NAME = re.compile(r"^wg[0-9]+$")
_PEER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_B64KEY = re.compile(r"^[A-Za-z0-9+/]{43}=$")


def validate_server(name: str, address: str, port: int) -> dict:
    if not _NAME.match(name or ""):
        raise ValueError("serveur : nom wg<N> requis (ex. wg0)")
    try:
        ipaddress.ip_interface(address)
    except ValueError:
        raise ValueError(f"address CIDR invalide: {address}")
    if not 1 <= int(port) <= 65535:
        raise ValueError("port 1..65535")
    return {"name": name, "address": address, "port": int(port)}


def genkeypair() -> dict:
    r = run("wg", "genkey", timeout=15, caller="vpn.keygen")
    if r.rc != 0 or not _B64KEY.match(r.out.strip()):
        raise ValueError(f"wg genkey KO: {r.out[:200]}")
    priv = r.out.strip()
    # derive la cle publique (argv fixe, entree via stdin, pas de shell)
    import subprocess, shutil
    exe = shutil.which("wg")
    p = subprocess.run([exe, "pubkey"], input=(priv + "\n"), capture_output=True,
                       text=True, timeout=15, shell=False)
    if p.returncode != 0:
        raise ValueError("derive pubkey KO")
    return {"private_key": priv, "public_key": p.stdout.strip()}


def validate_peer(name: str, public_key: str, allowed_ips: str,
                  endpoint: str = "", keepalive: int = 25) -> dict:
    if not _PEER.match(name or ""):
        raise ValueError("peer : nom invalide")
    if not _B64KEY.match(public_key or ""):
        raise ValueError("peer : cle publique WireGuard invalide")
    nets = []
    for cidr in (allowed_ips or "").split(","):
        cidr = cidr.strip()
        if not cidr:
            continue
        try:
            nets.append(str(ipaddress.ip_network(cidr, strict=False)))
        except ValueError:
            raise ValueError(f"allowed_ips invalide: {cidr}")
    if not nets:
        raise ValueError("allowed_ips requis (ex. 10.8.0.2/32)")
    if endpoint:
        host = endpoint.rsplit(":", 1)[0].strip("[]")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            import re as _re
            if not _re.match(r"^[A-Za-z0-9.-]+$", host):
                raise ValueError("endpoint invalide (host:port)")
        if ":" not in endpoint:
            raise ValueError("endpoint : port requis")
    if not 0 <= int(keepalive) <= 65535:
        raise ValueError("keepalive 0..65535")
    return {"name": name, "public_key": public_key,
            "allowed_ips": ", ".join(nets), "endpoint": endpoint,
            "keepalive": int(keepalive)}


def render_conf(server: dict, peers: list[dict]) -> str:
    lines = ["# Genere par InfraOS — ne pas editer", "[Interface]",
             f"Address = {server['address']}",
             f"ListenPort = {server['port']}",
             f"PrivateKey = {server['private_key']}", ""]
    for p in peers:
        lines += ["[Peer]", f"# {p['name']}",
                  f"PublicKey = {p['public_key']}"]
        if p.get("preshared_key"):
            lines.append(f"PresharedKey = {p['preshared_key']}")
        lines.append(f"AllowedIPs = {p['allowed_ips']}")
        if p.get("endpoint"):
            lines.append(f"Endpoint = {p['endpoint']}")
        if p.get("keepalive"):
            lines.append(f"PersistentKeepalive = {p['keepalive']}")
        lines.append("")
    return "\n".join(lines)


def write_conf(name: str, text: str) -> str:
    WG_DIR.mkdir(parents=True, exist_ok=True)
    import os
    path = WG_DIR / f"{name}.conf"
    path.write_text(text)
    os.chmod(path, 0o600)
    return str(path)


def status_iface(name: str) -> dict:
    r = run("wg", "show", name, "dump", timeout=15, caller="vpn.status")
    if r.rc != 0:
        return {"interface": name, "up": False, "detail": r.out[:300]}
    lines = [l for l in r.out.splitlines() if l.strip()]
    peers = len(lines) - 1 if lines else 0
    return {"interface": name, "up": True, "peers": peers,
            "detail": f"{peers} peers (dump)"}
