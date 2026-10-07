# SPDX-License-Identifier: GPL-3.0-or-later
"""IPAM — reseaux/sous-reseaux/hotes, allocation, liens DNS/DHCP.

Exemple : Network 192.168.20.0/24, gateway .254, hotes .10/.20/.50.
"""
from __future__ import annotations
import ipaddress
import re
from .db import get_session
from .models import IpamNetwork, IpamHost

_MAC = re.compile(r"^[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}$")


def validate_network(cidr: str, gateway: str = "", vlan: int = 0) -> dict:
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        raise ValueError(f"CIDR invalide: {cidr}")
    if gateway:
        try:
            g = ipaddress.ip_address(gateway)
        except ValueError:
            raise ValueError("gateway invalide")
        if g not in net:
            raise ValueError("gateway hors reseau")
    if not 0 <= int(vlan) <= 4094:
        raise ValueError("VLAN 0..4094")
    return {"cidr": str(net), "gateway": gateway, "vlan": int(vlan)}


def allocate(network_id: int, hostname: str = "", mac: str = "",
             kind: str = "static") -> dict:
    """Premiere IP libre (saute reseau/broadcast/gateway/existants)."""
    if mac and not _MAC.match(mac):
        raise ValueError(f"MAC invalide: {mac}")
    s = get_session()
    try:
        net = s.get(IpamNetwork, network_id)
        if not net:
            raise ValueError("reseau inconnu")
        taken = {h.ip for h in s.query(IpamHost).filter_by(network_id=network_id).all()}
        if net.gateway:
            taken.add(net.gateway)
        cidr = ipaddress.ip_network(net.cidr)
        for ip in cidr.hosts():
            sip = str(ip)
            if sip not in taken:
                h = IpamHost(network_id=network_id, ip=sip, mac=mac.lower(),
                             hostname=hostname, kind=kind)
                s.add(h)
                s.commit()
                return {"id": h.id, "ip": sip, "hostname": hostname, "kind": kind}
        raise ValueError("subnet plein")
    finally:
        s.close()


def usage(network_id: int) -> dict:
    s = get_session()
    try:
        net = s.get(IpamNetwork, network_id)
        if not net:
            raise ValueError("reseau inconnu")
        cidr = ipaddress.ip_network(net.cidr)
        total = cidr.num_addresses - 2 if cidr.version == 4 else cidr.num_addresses
        used = s.query(IpamHost).filter_by(network_id=network_id).count()
        hosts = [{"ip": h.ip, "mac": h.mac, "hostname": h.hostname, "kind": h.kind}
                 for h in s.query(IpamHost).filter_by(network_id=network_id)
                 .order_by(IpamHost.ip).all()]
        return {"network": net.cidr, "total": total, "used": used,
                "free": max(0, total - used), "hosts": hosts}
    finally:
        s.close()
