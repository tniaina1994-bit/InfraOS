# SPDX-License-Identifier: GPL-3.0-or-later
"""Monitoring — metriques serveur (psutil/systemd) + agent futur (Linux/Windows).

Serveur : CPU/RAM/disque/reseau/charge/processus/services/uptime/temperature.
Echantillons en DB (collecte explicite), historique, agents (register +
heartbeat + push, protocole docs/AGENT.md).
"""
from __future__ import annotations
import socket
import time
from .db import get_session
from .models import MonitoringSample, MonitoringAgent


def current() -> dict:
    import psutil
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    try:
        load = tuple(round(x, 2) for x in psutil.getloadavg())
    except (AttributeError, OSError):
        load = ()
    net = psutil.net_io_counters()
    boot = psutil.boot_time()
    procs = len(psutil.pids())
    temp = ""
    try:
        for name, entries in (psutil.sensors_temperatures() or {}).items():
            if entries:
                temp = f"{name}:{entries[0].current}C"
                break
    except (AttributeError, OSError):
        pass
    return {"hostname": socket.gethostname(), "cpu": cpu, "mem": round(mem.percent, 1),
            "disk": round(disk.percent, 1), "load1": load[0] if load else 0,
            "net_rx": net.bytes_recv, "net_tx": net.bytes_sent,
            "uptime": int(time.time() - boot), "processes": procs, "temp": temp}


def collect(host: str = "local") -> dict:
    m = current()
    s = get_session()
    try:
        s.add(MonitoringSample(host=host, cpu=int(m["cpu"]), mem=int(m["mem"]),
                               disk=int(m["disk"]), load1=str(m["load1"]),
                               net_rx=m["net_rx"], net_tx=m["net_tx"],
                               uptime=m["uptime"], temp=m["temp"]))
        s.commit()
        return {"host": host, **m}
    finally:
        s.close()


def history(host: str = "local", limit: int = 60) -> list[dict]:
    limit = max(1, min(int(limit), 500))
    s = get_session()
    try:
        rows = (s.query(MonitoringSample).filter_by(host=host)
                .order_by(MonitoringSample.id.desc()).limit(limit).all())
        return [{"ts": str(r.created_at), "cpu": r.cpu, "mem": r.mem,
                 "disk": r.disk, "load1": r.load1, "uptime": r.uptime,
                 "temp": r.temp} for r in reversed(rows)]
    finally:
        s.close()


def register_agent(hostname: str, os: str, token: str) -> dict:
    import re
    if not re.match(r"^[A-Za-z0-9_.-]{1,128}$", hostname or ""):
        raise ValueError("hostname agent invalide")
    if os not in ("linux", "windows"):
        raise ValueError("os agent: linux|windows")
    if len(token or "") < 16:
        raise ValueError("token agent 16+ caracteres")
    s = get_session()
    try:
        a = s.query(MonitoringAgent).filter_by(hostname=hostname).first()
        if a:
            a.os, a.token = os, token
        else:
            s.add(MonitoringAgent(hostname=hostname, os=os, token=token))
        s.commit()
        return {"hostname": hostname, "os": os}
    finally:
        s.close()


def agent_push(hostname: str, token: str, metrics: dict) -> dict:
    s = get_session()
    try:
        a = s.query(MonitoringAgent).filter_by(hostname=hostname).first()
        if not a or a.token != token:
            raise ValueError("agent inconnu ou token invalide")
        from datetime import datetime, timezone
        a.last_seen = datetime.now(timezone.utc)
        s.add(MonitoringSample(host=hostname, cpu=int(metrics.get("cpu", 0)),
                               mem=int(metrics.get("mem", 0)), disk=int(metrics.get("disk", 0)),
                               load1=str(metrics.get("load1", "")),
                               net_rx=int(metrics.get("net_rx", 0)),
                               net_tx=int(metrics.get("net_tx", 0)),
                               uptime=int(metrics.get("uptime", 0)),
                               temp=str(metrics.get("temp", ""))))
        s.commit()
        return {"host": hostname, "stored": True}
    finally:
        s.close()


def agents() -> list[dict]:
    s = get_session()
    try:
        return [{"hostname": a.hostname, "os": a.os,
                 "last_seen": str(a.last_seen) if a.last_seen else None}
                for a in s.query(MonitoringAgent).all()]
    finally:
        s.close()
