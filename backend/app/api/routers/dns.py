"""DNS — zones, records (A/AAAA/CNAME/MX/TXT/PTR/NS), forwarders, apply BIND9.

Lecture : operator+. Ecritures + apply : admin (audite, evenement).
"""
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
from infraos.models import DnsZone, DnsRecord
from infraos import dns_validate as dv
from infraos.modules import dns as dns_mod
from infraos import event_manager as em
from deps import require_role

router = APIRouter()


class ZoneBody(BaseModel):
    name: str
    kind: str = "master"
    reverse: bool = False
    ttl: int = 3600
    forwarders: list[str] = []
    enabled: bool = True


class RecordBody(BaseModel):
    name: str
    rtype: str
    value: str
    priority: int = 0
    ttl: int = 0


def _zone_out(z) -> dict:
    return {"id": z.id, "name": z.name, "kind": z.kind, "reverse": z.reverse,
            "ttl": z.ttl, "forwarders": json.loads(z.forwarders or "[]"),
            "enabled": z.enabled}


@router.get("/zones")
def list_zones(user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        return {"zones": [_zone_out(z) for z in db.query(DnsZone).order_by(DnsZone.name).all()]}
    finally:
        db.close()


@router.post("/zones")
def create_zone(body: ZoneBody, user: dict = Depends(require_role("admin"))):
    if body.kind not in ("master", "forward"):
        raise HTTPException(400, "kind: master|forward")
    try:
        name = dv.zone_name(body.name, body.reverse)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if body.kind == "forward" and not body.forwarders:
        raise HTTPException(400, "zone forward : forwarders requis")
    for f in body.forwarders:
        try:
            __import__("ipaddress").ip_address(f)
        except ValueError:
            raise HTTPException(400, f"forwarder invalide: {f}")
    db = get_session()
    try:
        if db.query(DnsZone).filter_by(name=name).first():
            raise HTTPException(409, "zone existe")
        z = DnsZone(name=name, kind=body.kind, reverse=body.reverse,
                    ttl=body.ttl, forwarders=json.dumps(body.forwarders),
                    enabled=body.enabled)
        db.add(z)
        db.commit()
        em.publish("config.updated", user["username"], f"dns zone+ {name}")
        return _zone_out(z)
    finally:
        db.close()


@router.delete("/zones/{zone}")
def delete_zone(zone: str, user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        z = db.query(DnsZone).filter_by(name=zone).first()
        if not z:
            raise HTTPException(404, "zone inconnue")
        db.query(DnsRecord).filter_by(zone_id=z.id).delete()
        db.delete(z)
        db.commit()
        em.publish("config.updated", user["username"], f"dns zone- {zone}")
        return {"deleted": zone}
    finally:
        db.close()


@router.get("/zones/{zone}/records")
def list_records(zone: str, user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        z = db.query(DnsZone).filter_by(name=zone).first()
        if not z:
            raise HTTPException(404, "zone inconnue")
        recs = db.query(DnsRecord).filter_by(zone_id=z.id).order_by(DnsRecord.name).all()
        return {"zone": zone, "records": [
            {"id": r.id, "name": r.name, "rtype": r.rtype, "value": r.value,
             "priority": r.priority, "ttl": r.ttl} for r in recs]}
    finally:
        db.close()


@router.post("/zones/{zone}/records")
def create_record(zone: str, body: RecordBody, user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        z = db.query(DnsZone).filter_by(name=zone).first()
        if not z:
            raise HTTPException(404, "zone inconnue")
        if z.kind == "forward":
            raise HTTPException(400, "zone forward : pas de records")
        try:
            clean = dv.record(body.rtype, body.name, body.value, body.priority)
        except ValueError as e:
            raise HTTPException(400, str(e))
        existing = [{"id": r.id, "name": r.name, "rtype": r.rtype}
                    for r in db.query(DnsRecord).filter_by(zone_id=z.id).all()]
        try:
            dv.check_cname_exclusive(existing, clean)
        except ValueError as e:
            raise HTTPException(400, str(e))
        r = DnsRecord(zone_id=z.id, ttl=body.ttl or 0, **clean)
        db.add(r)
        db.commit()
        return {"id": r.id, **clean}
    finally:
        db.close()


@router.delete("/records/{rid}")
def delete_record(rid: int, user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        r = db.get(DnsRecord, rid)
        if not r:
            raise HTTPException(404, "record inconnu")
        db.delete(r)
        db.commit()
        return {"deleted": rid}
    finally:
        db.close()


@router.get("/servers")
def get_servers(user: dict = Depends(require_role("operator"))):
    return {"forwarders": dns_mod.get_forwarders(), "backend": dns_mod.backend_kind()}


@router.put("/servers")
def put_servers(body: dict, user: dict = Depends(require_role("admin"))):
    try:
        fwd = dns_mod.set_forwarders(body.get("forwarders", []))
    except ValueError as e:
        raise HTTPException(400, str(e))
    em.publish("config.updated", user["username"], f"dns forwarders={fwd}")
    return {"forwarders": fwd}


@router.post("/apply")
def apply(user: dict = Depends(require_role("admin"))):
    out = dns_mod.apply()
    em.publish("config.updated", user["username"], f"dns apply applied={out.get('applied')}")
    return out
