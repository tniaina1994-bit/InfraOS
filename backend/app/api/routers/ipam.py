"""IPAM — reseaux, hotes, allocation (admin ecritures)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.db import get_session
from infraos.models import IpamNetwork, IpamHost
from infraos import ipam as ipam_mod
from infraos import event_manager as em
from deps import require_role

router = APIRouter()


class NetworkBody(BaseModel):
    name: str
    cidr: str
    gateway: str = ""
    vlan: int = 0
    description: str = ""


class HostBody(BaseModel):
    ip: str = ""
    mac: str = ""
    hostname: str = ""
    kind: str = "static"
    auto: bool = True


@router.get("/networks")
def list_networks(user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        return {"networks": [{"id": n.id, "name": n.name, "cidr": n.cidr,
                              "gateway": n.gateway, "vlan": n.vlan,
                              "description": n.description}
                             for n in db.query(IpamNetwork).all()]}
    finally:
        db.close()


@router.post("/networks")
def create_network(body: NetworkBody, user: dict = Depends(require_role("admin"))):
    try:
        clean = ipam_mod.validate_network(body.cidr, body.gateway, body.vlan)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db = get_session()
    try:
        if db.query(IpamNetwork).filter_by(name=body.name).first():
            raise HTTPException(409, "reseau existe")
        n = IpamNetwork(name=body.name, description=body.description, **clean)
        db.add(n)
        db.commit()
        # enregistre la gateway comme hote reserve si definie
        if clean["gateway"]:
            db.add(IpamHost(network_id=n.id, ip=clean["gateway"], hostname="gateway", kind="gateway"))
            db.commit()
        em.publish("config.updated", user["username"], f"ipam net+ {body.name}")
        return {"id": n.id, "name": body.name, **clean}
    finally:
        db.close()


@router.get("/networks/{nid}")
def network_usage(nid: int, user: dict = Depends(require_role("operator"))):
    try:
        return ipam_mod.usage(nid)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/networks/{nid}/hosts")
def add_host(nid: int, body: HostBody, user: dict = Depends(require_role("admin"))):
    if body.auto or not body.ip:
        try:
            out = ipam_mod.allocate(nid, body.hostname, body.mac, body.kind)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return out
    db = get_session()
    try:
        net = db.get(IpamNetwork, nid)
        if not net:
            raise HTTPException(404, "reseau inconnu")
        import ipaddress
        try:
            if ipaddress.ip_address(body.ip) not in ipaddress.ip_network(net.cidr):
                raise ValueError("IP hors reseau")
        except ValueError as e:
            raise HTTPException(400, str(e))
        if db.query(IpamHost).filter_by(network_id=nid, ip=body.ip).first():
            raise HTTPException(409, "IP deja allouee")
        h = IpamHost(network_id=nid, ip=body.ip, mac=body.mac,
                     hostname=body.hostname, kind=body.kind)
        db.add(h)
        db.commit()
        return {"id": h.id, "ip": body.ip}
    finally:
        db.close()


@router.delete("/networks/{nid}")
def delete_network(nid: int, user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        n = db.get(IpamNetwork, nid)
        if not n:
            raise HTTPException(404, "reseau inconnu")
        db.query(IpamHost).filter_by(network_id=nid).delete()
        db.delete(n)
        db.commit()
        return {"deleted": nid}
    finally:
        db.close()
