# SPDX-License-Identifier: GPL-3.0-or-later
"""Firewall nftables — modele FirewallRule -> ruleset, check avant apply.

Philo: JAMAIS de shell/nft libre depuis le Web. Les regles DB sont rendues
en nftables (table inet filter + nat), verifiees (`nft -c -f`, argv fixe),
puis appliquees (`nft -f`). En LXC non-privilegie l'apply echoue proprement
(rc != 0, degrade documente) sans rien casser.
"""
from __future__ import annotations
import ipaddress
import re
import subprocess
import shutil
from pathlib import Path
from .logging_conf import get_logger

log = get_logger("infraos.nft")
CONF = Path("/etc/nftables.infraos.conf")
_IF = re.compile(r"^[A-Za-z0-9@:_.-]+$")
CHAINS = {"input", "forward", "output", "prerouting", "postrouting"}
ACTIONS = {"accept", "drop", "dnat", "masquerade", "log"}
PROTOS = {"all", "tcp", "udp", "icmp"}


def validate_rule(r: dict) -> dict:
    chain = (r.get("chain") or "input").lower()
    action = (r.get("action") or "accept").lower()
    proto = (r.get("proto") or "all").lower()
    if chain not in CHAINS:
        raise ValueError(f"chain: {sorted(CHAINS)}")
    if action not in ACTIONS:
        raise ValueError(f"action: {sorted(ACTIONS)}")
    if proto not in PROTOS:
        raise ValueError(f"proto: {sorted(PROTOS)}")
    for k in ("src", "dst"):
        v = (r.get(k) or "").strip()
        if v:
            try:
                ipaddress.ip_network(v, strict=False)
            except ValueError:
                raise ValueError(f"{k} CIDR invalide: {v}")
    dport = int(r.get("dport") or 0)
    if not 0 <= dport <= 65535:
        raise ValueError("dport 0..65535")
    if proto == "all" and dport:
        raise ValueError("dport exige proto tcp/udp")
    for k in ("in_if", "out_if"):
        v = (r.get(k) or "").strip()
        if v and (not _IF.match(v) or len(v) > 32):
            raise ValueError(f"{k} invalide")
    nat_to = (r.get("nat_to") or "").strip()
    if action == "dnat":
        if chain != "prerouting" or not nat_to:
            raise ValueError("dnat : chain=prerouting + nat_to requis (ip[:port])")
        host = nat_to.split(":")[0]
        try:
            ipaddress.ip_address(host)
        except ValueError:
            raise ValueError("nat_to IP invalide")
    if action == "masquerade" and chain != "postrouting":
        raise ValueError("masquerade : chain=postrouting")
    return {"name": (r.get("name") or "rule")[:64], "chain": chain, "action": action,
            "proto": proto, "src": (r.get("src") or "").strip(),
            "dst": (r.get("dst") or "").strip(), "dport": dport,
            "in_if": (r.get("in_if") or "").strip(), "out_if": (r.get("out_if") or "").strip(),
            "nat_to": nat_to, "log": bool(r.get("log")),
            "position": int(r.get("position") or 100), "enabled": bool(r.get("enabled", True))}


def _stmt(r: dict) -> str:
    parts = []
    if r["in_if"] and r["chain"] in ("input", "forward", "prerouting"):
        parts.append(f'iifname "{r["in_if"]}"')
    if r["out_if"] and r["chain"] in ("forward", "output", "postrouting"):
        parts.append(f'oifname "{r["out_if"]}"')
    if r["proto"] != "all":
        parts.append(r["proto"])
    if r["src"]:
        parts.append(f"ip saddr {r['src']}")
    if r["dst"]:
        parts.append(f"ip daddr {r['dst']}")
    if r["dport"]:
        parts.append(f"dport {r['dport']}")
    if r["log"]:
        parts.append('log prefix "infraos: "')
    if r["action"] == "accept":
        parts.append("accept")
    elif r["action"] == "drop":
        parts.append("drop")
    elif r["action"] == "dnat":
        parts.append(f"dnat to {r['nat_to']}")
    elif r["action"] == "masquerade":
        parts.append("masquerade")
    elif r["action"] == "log":
        pass  # log seul : pas de verdict -> la chaine continue
    base = " ".join(parts) if parts else "accept"
    return f'    # {r["name"]}\n    {base}'


def render(rules: list[dict], input_policy: str = "accept",
           forward_policy: str = "accept") -> str:
    if input_policy not in ("accept", "drop") or forward_policy not in ("accept", "drop"):
        raise ValueError("policy: accept|drop")
    by_chain: dict[str, list[str]] = {}
    for raw in sorted(rules, key=lambda x: (x.get("position", 100), x.get("name", ""))):
        r = validate_rule(raw)
        if not r["enabled"]:
            continue
        by_chain.setdefault(r["chain"], []).append(_stmt(r))
    nat_pre = "\n".join(by_chain.pop("prerouting", []))
    nat_post = "\n".join(by_chain.pop("postrouting", []))
    filt = "\n".join(f"  chain {c} {{\n" +
                     (f"    type filter hook {c} priority 0; policy {input_policy if c == 'input' else (forward_policy if c == 'forward' else 'accept')};\n" if c in ("input", "forward", "output") else "") +
                     ("\n".join(body) + "\n" if body else "") + "  }"
                     for c, body in sorted(by_chain.items()))
    return ("#!/usr/sbin/nft -f\n# Genere par InfraOS — ne pas editer\n"
            "flush ruleset\n\ntable inet filter {\n" + (filt or "  # (aucune regle)") + "\n}\n\n"
            "table ip nat {\n"
            "  chain prerouting { type nat hook prerouting priority -100;\n" + (nat_pre + "\n" if nat_pre else "") + "  }\n"
            "  chain postrouting { type nat hook postrouting priority 100;\n" + (nat_post + "\n" if nat_post else "") + "  }\n}\n")


def check(path: Path = CONF) -> dict:
    """Validation seule (`nft -c -f`, argv fixe, jamais d'entree shell)."""
    exe = shutil.which("nft")
    if not exe:
        return {"ok": False, "detail": "nft absent"}
    try:
        p = subprocess.run([exe, "-c", "-f", str(path)], capture_output=True,
                           text=True, timeout=30, shell=False)
        return {"ok": p.returncode == 0, "detail": (p.stdout + p.stderr)[-2000:] or "nft -c OK"}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


def apply(ruleset: str) -> dict:
    """Ecrit + check + apply. Echec propre en LXC (degrade)."""
    try:
        CONF.parent.mkdir(parents=True, exist_ok=True)
        if CONF.exists():
            Path(str(CONF) + ".infraos-bak").write_bytes(CONF.read_bytes())
        CONF.write_text(ruleset)
    except OSError as e:
        return {"applied": False, "detail": f"ecriture impossible: {e}"}
    c = check()
    if not c["ok"]:
        return {"applied": False, "stage": "check", **c}
    # apply reel : argv fixe, pas d'entree utilisateur
    exe = shutil.which("nft")
    try:
        p = subprocess.run([exe, "-f", str(CONF)], capture_output=True,
                           text=True, timeout=30, shell=False)
        ok = p.returncode == 0
        detail = (p.stdout + p.stderr)[-2000:]
        if not ok:
            detail += " (LXC non-privilegie ? regles hotes via Proxmox)"
        return {"applied": ok, "stage": "apply", "detail": detail or "nft -f OK"}
    except Exception as e:
        return {"applied": False, "stage": "apply", "detail": str(e)}
