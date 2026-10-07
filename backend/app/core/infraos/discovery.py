# SPDX-License-Identifier: GPL-3.0-or-later
"""Decouverte reseau — nmap lance EXPLICITEMENT par l'admin (jamais auto).

Profils : ping (-sn : ARP/ICMP, hotes+MAC), fast (-F : ports courants),
os (-O : OS, 1 hote). Cible : CIDR <= /16 ou IP unique (jamais 0.0.0.0/0).
Sortie XML parsee (stdlib), stockee (scans + hotes), comparaisons entre scans.
"""
from __future__ import annotations
import ipaddress
import xml.etree.ElementTree as ET
from .exec import run
from .logging_conf import get_logger

log = get_logger("infraos.discovery")
PROFILES = {"ping": ["-sn"], "fast": ["-F"], "os": ["-O"]}


def validate_target(target: str, profile: str) -> dict:
    if profile not in PROFILES:
        raise ValueError(f"profil: {sorted(PROFILES)}")
    t = (target or "").strip()
    try:
        if "/" in t:
            net = ipaddress.ip_network(t, strict=False)
            if net.prefixlen < 16:
                raise ValueError("CIDR /16 minimum (scan trop large refuse)")
            if net.is_unspecified:
                raise ValueError("0.0.0.0/0 interdit")
        else:
            ipaddress.ip_address(t)
            net = t
    except ValueError as e:
        raise ValueError(f"cible invalide: {e}")
    return {"target": t, "profile": profile}


def scan(target: str, profile: str = "ping", timeout: int = 300) -> list[dict]:
    v = validate_target(target, profile)
    args = PROFILES[v["profile"]] + ["-oX", "-", v["target"]]
    r = run("nmap", *args, timeout=timeout, caller="discovery.scan")
    if r.rc != 0 and "<nmaprun" not in r.out:
        raise ValueError(f"nmap KO: {r.out[:300]}")
    return parse_xml(r.out)


def parse_xml(xml_text: str) -> list[dict]:
    hosts = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return hosts
    for h in root.findall("host"):
        if (h.find("status") is not None and h.find("status").get("state") != "up"):
            continue
        ip = mac = hostname = osname = ""
        for a in h.findall("address"):
            if a.get("addrtype") in ("ipv4", "ipv6") and not ip:
                ip = a.get("addr", "")
            if a.get("addrtype") == "mac":
                mac = a.get("addr", "").lower()
        for hn in h.findall("hostnames/hostname"):
            if not hostname:
                hostname = hn.get("name", "")
        ports = []
        for p in h.findall("ports/port"):
            st = p.find("state")
            if st is not None and st.get("state") == "open":
                svc = p.find("service")
                ports.append({"port": int(p.get("portid", 0)), "proto": p.get("protocol", ""),
                              "service": svc.get("name", "") if svc is not None else ""})
        om = h.find("os/osmatch")
        if om is not None:
            osname = om.get("name", "")
        if ip:
            hosts.append({"ip": ip, "mac": mac, "hostname": hostname,
                          "ports": ports, "os": osname})
    return hosts


def arp_table() -> list[dict]:
    """Table ARP locale (lecture /proc, sans scan)."""
    out = []
    try:
        with open("/proc/net/arp") as f:
            for line in f.read().splitlines()[1:]:
                p = line.split()
                if len(p) >= 6 and ":" in p[3]:
                    out.append({"ip": p[0], "mac": p[3].lower(), "iface": p[5]})
    except OSError:
        pass
    return out


def compare(old: list[dict], new: list[dict]) -> dict:
    o = {h["ip"]: h for h in old}
    n = {h["ip"]: h for h in new}
    return {"new": sorted(set(n) - set(o)),
            "gone": sorted(set(o) - set(n)),
            "changed": sorted(ip for ip in set(o) & set(n) if o[ip] != n[ip])}
