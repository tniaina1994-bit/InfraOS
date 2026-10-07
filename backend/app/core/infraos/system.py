"""System inspectors: OS, services, network. Read-only, safe in LXC.

Philo securite: aucun appel shell direct — tout passe par exec.run()
(allow-list). Aucune entree Web n'atteint un shell.
"""
from __future__ import annotations
import platform
import socket
import psutil
from .exec import run


def os_info() -> dict:
    info = {
        "hostname": socket.gethostname(),
        "kernel": platform.release(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "pretty": "",
        "virt": "unknown",
    }
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    info["pretty"] = line.split("=", 1)[1].strip().strip('"')
    except FileNotFoundError:
        info["pretty"] = platform.platform()
    exe_found = run("systemd-detect-virt", caller="system.os_info")
    info["virt"] = exe_found.out.strip() if exe_found.rc == 0 and exe_found.out.strip() else (
        "none" if exe_found.rc == 127 else "unknown")
    try:
        info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        info["mem"] = dict(psutil.virtual_memory()._asdict())
        info["disk"] = dict(psutil.disk_usage("/")._asdict())
    except Exception as e:
        info["metrics_error"] = str(e)
    return info


IMPORTANT_SERVICES = ["ssh", "named", "kea-dhcp4-server", "isc-dhcp-server",
                      "nftables", "smbd", "samba-ad-dc", "nginx", "infraos-api"]


def services_status() -> list[dict]:
    out = []
    for svc in IMPORTANT_SERVICES:
        # allow-list: systemctl is-active <nom fixe> — le nom vient d'une
        # constante interne, jamais d'une entree utilisateur brute.
        r = run("systemctl", "is-active", svc, caller="system.services")
        state = r.out.strip() or "unknown"
        out.append({"name": svc, "active": state})
    return out


def net_interfaces() -> list[dict]:
    res = []
    try:
        for name, addrs in psutil.net_if_addrs().items():
            stats = psutil.net_if_stats().get(name)
            res.append({
                "name": name,
                "up": bool(stats.isup) if stats else None,
                "speed_mbps": getattr(stats, "speed", None) if stats else None,
                "addresses": [{"family": str(a.family), "address": a.address,
                               "netmask": a.netmask} for a in addrs],
            })
    except Exception as e:
        return [{"error": str(e)}]
    return res
