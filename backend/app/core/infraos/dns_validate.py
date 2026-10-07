# SPDX-License-Identifier: GPL-3.0-or-later
"""Validation DNS — A/AAAA/CNAME/MX/TXT/PTR/NS, zones forward + reverse."""
from __future__ import annotations
import ipaddress
import re

_HOST = re.compile(r"^(?:@|[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,251}[A-Za-z0-9])?)$")
_FQDN = re.compile(r"^(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}\.?$")
_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
_ZONE = re.compile(rf"^{_LABEL}(?:\.{_LABEL})*\.?$")
_ARPA = re.compile(r"^[0-9.]+in-addr\.arpa\.?$|^[0-9a-f.:]+ip6\.arpa\.?$", re.IGNORECASE)
TYPES = {"A", "AAAA", "CNAME", "MX", "TXT", "PTR", "NS"}


def zone_name(name: str, reverse: bool = False) -> str:
    n = (name or "").strip().lower()
    if not n or len(n) > 253:
        raise ValueError("nom de zone vide ou trop long")
    is_arpa = bool(_ARPA.match(n))
    if reverse and not is_arpa:
        raise ValueError("zone reverse : suffixe in-addr.arpa / ip6.arpa requis")
    if not reverse and is_arpa:
        raise ValueError("zone forward : nom arpa interdit (creez une reverse)")
    if not reverse and not _ZONE.match(n):
        raise ValueError(f"nom de zone invalide: {n}")
    return n.rstrip(".")


def _fqdn_or_host(value: str, field: str) -> str:
    v = (value or "").strip()
    if not v or len(v) > 253:
        raise ValueError(f"{field}: valeur vide ou trop longue")
    if not (_FQDN.match(v) or _HOST.match(v)):
        raise ValueError(f"{field}: nom invalide: {v}")
    return v


def record(rtype: str, name: str, value: str, priority: int = 0) -> dict:
    rt = (rtype or "").upper()
    if rt not in TYPES:
        raise ValueError(f"type inconnu: {rt} (attendus: {sorted(TYPES)})")
    n = (name or "").strip()
    if not n or not _HOST.match(n):
        raise ValueError(f"nom d'enregistrement invalide: {n}")
    v = (value or "").strip()
    if rt == "A":
        try:
            ipaddress.IPv4Address(v)
        except ValueError:
            raise ValueError(f"A: IPv4 invalide: {v}")
    elif rt == "AAAA":
        try:
            ipaddress.IPv6Address(v)
        except ValueError:
            raise ValueError(f"AAAA: IPv6 invalide: {v}")
    elif rt in ("CNAME", "NS"):
        v = _fqdn_or_host(v, rt)
    elif rt == "MX":
        if not 0 <= int(priority) <= 65535:
            raise ValueError("MX: priorite 0..65535")
        v = _fqdn_or_host(v, "MX")
    elif rt == "TXT":
        if len(v) > 2048:
            raise ValueError("TXT: 2048 caracteres max")
        v = v.replace('"', '\\"')
    elif rt == "PTR":
        v = _fqdn_or_host(v, "PTR")
        try:
            int(n)
        except ValueError:
            raise ValueError("PTR: nom = dernier octet/nibble (ex. 10)")
    if len(n) > 253:
        raise ValueError("nom trop long")
    return {"rtype": rt, "name": n, "value": v, "priority": int(priority)}


def check_cname_exclusive(existing: list[dict], new: dict) -> None:
    """Un nom en CNAME ne porte aucun autre record (RFC 1034)."""
    for r in existing:
        if r["name"] == new["name"] and r["id"] != new.get("id"):
            if r["rtype"] == "CNAME" or new["rtype"] == "CNAME":
                raise ValueError(f"CNAME exclusif sur {new['name']} (conflit {r['rtype']})")
