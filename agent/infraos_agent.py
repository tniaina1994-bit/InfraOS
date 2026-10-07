#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Agent de reference InfraOS — Linux + Windows (stdlib + psutil).

Boucle : collecte -> push HTTPS -> 60s. Push-only (aucune ecoute).
Config : agent.yaml (server, token 0600, hostname auto). Logs stdout
(journald / planificateur). Token jamais affiche.
"""
from __future__ import annotations
import json
import os
import platform
import socket
import sys
import time
import urllib.request

INTERVAL = int(os.getenv("INFRAOS_AGENT_INTERVAL", "60"))


def load_config(path: str) -> dict:
    # format "cle: valeur" volontairement sans dependance yaml
    cfg = {"server": "https://infraos.local", "token": "", "insecure": False}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                k, v = line.split(":", 1)
                cfg[k.strip()] = v.strip().strip('"')
    except OSError as e:
        print(f"config illisible {path}: {e}", file=sys.stderr)
        sys.exit(2)
    if not cfg.get("token"):
        print("token manquant dans agent.yaml", file=sys.stderr)
        sys.exit(2)
    return cfg


def collect() -> dict:
    import psutil
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/" if os.name != "nt" else "C:\\").percent
    try:
        load1 = round(psutil.getloadavg()[0], 2)
    except (AttributeError, OSError):
        load1 = 0
    net = psutil.net_io_counters()
    uptime = int(time.time() - psutil.boot_time())
    temp = ""
    try:
        for name, entries in (psutil.sensors_temperatures() or {}).items():
            if entries:
                temp = f"{name}:{entries[0].current}C"
                break
    except (AttributeError, OSError):
        pass
    procs = []
    try:
        for p in sorted(psutil.process_iter(["pid", "name", "cpu_percent"]),
                        key=lambda x: x.info.get("cpu_percent") or 0,
                        reverse=True)[:5]:
            procs.append({"pid": p.info["pid"], "name": p.info["name"]})
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return {"cpu": cpu, "mem": mem, "disk": disk, "load1": load1,
            "net_rx": net.bytes_recv, "net_tx": net.bytes_sent,
            "uptime": uptime, "temp": temp, "processes": procs,
            "os_info": f"{platform.system()} {platform.release()}"}


def push(server: str, hostname: str, token: str, metrics: dict) -> bool:
    body = json.dumps({"hostname": hostname, "token": token,
                       "metrics": metrics}).encode()
    req = urllib.request.Request(server.rstrip("/") + "/api/v1/monitoring/agents/push",
                                 data=body, headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception as e:
        print(f"push KO: {e}", file=sys.stderr)
        return False


def main() -> int:
    base = os.path.dirname(os.path.abspath(__file__))
    cfg = load_config(os.path.join(base, "agent.yaml"))
    hostname = socket.gethostname()
    print(f"infraos-agent -> {cfg['server']} as {hostname} "
          f"({platform.system()}) toutes les {INTERVAL}s")
    while True:
        ok = push(cfg["server"], hostname, cfg["token"], collect())
        print(f"push {'OK' if ok else 'KO'}", flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
