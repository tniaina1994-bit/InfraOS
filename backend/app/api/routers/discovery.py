"""Decouverte reseau — scans explicites admin, historique, comparaison."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import json
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.db import get_session
from infraos.models import DiscoveryScan, DiscoveryHost
from infraos import discovery as disc
from infraos import event_manager as em
from deps import require_role

router = APIRouter()


class ScanBody(BaseModel):
    target: str
    profile: str = "ping"


@router.post("/scans")
def run_scan(body: ScanBody, user: dict = Depends(require_role("admin"))):
    try:
        v = disc.validate_target(body.target, body.profile)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db = get_session()
    try:
        sc = DiscoveryScan(target=v["target"], profile=v["profile"], status="running")
        db.add(sc)
        db.commit()
        sid = sc.id
    finally:
        db.close()
    try:
        hosts = disc.scan(v["target"], v["profile"])
    except ValueError as e:
        raise HTTPException(500, str(e))
    db = get_session()
    try:
        sc = db.get(DiscoveryScan, sid)
        sc.status = "done"
        sc.hosts_up = len(hosts)
        for h in hosts:
            db.add(DiscoveryHost(scan_id=sid, ip=h["ip"], mac=h["mac"],
                                 hostname=h["hostname"],
                                 ports=json.dumps(h["ports"]), os=h["os"]))
        db.commit()
        em.publish("config.updated", user["username"],
                   f"discovery scan {v['target']} {len(hosts)} hotes")
        return {"scan_id": sid, "hosts_up": len(hosts), "hosts": hosts}
    finally:
        db.close()


@router.get("/scans")
def list_scans(user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        rows = db.query(DiscoveryScan).order_by(DiscoveryScan.id.desc()).limit(20).all()
        return {"scans": [{"id": s.id, "target": s.target, "profile": s.profile,
                          "status": s.status, "hosts_up": s.hosts_up,
                          "created_at": str(s.created_at)} for s in rows]}
    finally:
        db.close()


@router.get("/scans/{sid}")
def scan_detail(sid: int, user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        hosts = db.query(DiscoveryHost).filter_by(scan_id=sid).all()
        return {"scan_id": sid, "hosts": [
            {"ip": h.ip, "mac": h.mac, "hostname": h.hostname,
             "ports": json.loads(h.ports or "[]"), "os": h.os} for h in hosts]}
    finally:
        db.close()


@router.get("/compare")
def compare_scans(a: int, b: int, user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        def hosts(sid):
            return [{"ip": h.ip, "mac": h.mac, "hostname": h.hostname,
                     "ports": h.ports, "os": h.os}
                    for h in db.query(DiscoveryHost).filter_by(scan_id=sid).all()]
        return {"a": a, "b": b, **disc.compare(hosts(a), hosts(b))}
    finally:
        db.close()


@router.get("/arp")
def arp(user: dict = Depends(require_role("operator"))):
    return {"entries": disc.arp_table()}
