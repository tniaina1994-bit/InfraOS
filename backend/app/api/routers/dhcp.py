"""DHCP Kea — scopes, reservations, baux, apply (admin ecritures)."""
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
from infraos.models import DhcpScope, DhcpReservation
from infraos import dhcp as kea
from infraos import event_manager as em
from deps import require_role

router = APIRouter()


class ScopeBody(BaseModel):
    name: str
    subnet: str
    pool_start: str
    pool_end: str
    gateway: str = ""
    dns: list[str] = []
    domain: str = ""
    lease_valid: int = 3600
    lease_max: int = 7200
    enabled: bool = True


class ReservationBody(BaseModel):
    mac: str
    ip: str
    hostname: str = ""


def _scope_out(s) -> dict:
    return {"id": s.id, "name": s.name, "subnet": s.subnet,
            "pool_start": s.pool_start, "pool_end": s.pool_end,
            "gateway": s.gateway, "dns": json.loads(s.dns or "[]"),
            "domain": s.domain, "lease_valid": s.lease_valid,
            "lease_max": s.lease_max, "enabled": s.enabled}


@router.get("/scopes")
def list_scopes(user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        return {"scopes": [_scope_out(s) for s in db.query(DhcpScope).all()]}
    finally:
        db.close()


@router.post("/scopes")
def create_scope(body: ScopeBody, user: dict = Depends(require_role("admin"))):
    try:
        kea.validate_scope(body.subnet, body.pool_start, body.pool_end, body.gateway)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db = get_session()
    try:
        if db.query(DhcpScope).filter_by(name=body.name).first():
            raise HTTPException(409, "scope existe")
        s = DhcpScope(name=body.name, subnet=body.subnet, pool_start=body.pool_start,
                      pool_end=body.pool_end, gateway=body.gateway,
                      dns=json.dumps(body.dns), domain=body.domain,
                      lease_valid=body.lease_valid, lease_max=body.lease_max,
                      enabled=body.enabled)
        db.add(s)
        db.commit()
        em.publish("config.updated", user["username"], f"dhcp scope+ {body.name}")
        return _scope_out(s)
    finally:
        db.close()


@router.delete("/scopes/{sid}")
def delete_scope(sid: int, user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        s = db.get(DhcpScope, sid)
        if not s:
            raise HTTPException(404, "scope inconnu")
        db.query(DhcpReservation).filter_by(scope_id=sid).delete()
        db.delete(s)
        db.commit()
        return {"deleted": sid}
    finally:
        db.close()


@router.get("/scopes/{sid}/reservations")
def list_reservations(sid: int, user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        rows = db.query(DhcpReservation).filter_by(scope_id=sid).all()
        return {"reservations": [{"id": r.id, "mac": r.mac, "ip": r.ip,
                                 "hostname": r.hostname} for r in rows]}
    finally:
        db.close()


@router.post("/scopes/{sid}/reservations")
def create_reservation(sid: int, body: ReservationBody,
                       user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        s = db.get(DhcpScope, sid)
        if not s:
            raise HTTPException(404, "scope inconnu")
        try:
            clean = kea.validate_reservation(body.mac, body.ip,
                                             {"subnet": s.subnet})
        except ValueError as e:
            raise HTTPException(400, str(e))
        db.add(DhcpReservation(scope_id=sid, hostname=body.hostname, **clean))
        db.commit()
        return clean
    finally:
        db.close()


@router.get("/leases")
def get_leases(limit: int = 100, user: dict = Depends(require_role("operator"))):
    return kea.leases(limit)


@router.post("/apply")
def apply(user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        scopes = []
        for s in db.query(DhcpScope).all():
            res = [{"mac": r.mac, "ip": r.ip, "hostname": r.hostname}
                   for r in db.query(DhcpReservation).filter_by(scope_id=s.id).all()]
            scopes.append({**_scope_out(s), "reservations": res})
    finally:
        db.close()
    res = kea.write_and_check(kea.render_kea(scopes))
    if not res["ok"]:
        return {"applied": False, "stage": "check", **res}
    rel = kea.reload()
    em.publish("config.updated", user["username"], f"dhcp apply rc={rel['rc']}")
    return {"applied": rel["rc"] == 0, "stage": "reload", **rel}
