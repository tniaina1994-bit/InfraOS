"""VPN WireGuard — serveurs, peers, cles, statut (admin ecritures)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.db import get_session
from infraos.models import VpnServer, VpnPeer
from infraos import wireguard as wg
from infraos import service_manager as sm
from infraos import event_manager as em
from deps import require_role

router = APIRouter()


class ServerBody(BaseModel):
    name: str = "wg0"
    address: str = "10.8.0.1/24"
    port: int = 51820


class PeerBody(BaseModel):
    name: str
    public_key: str = ""
    preshared_key: str = ""
    allowed_ips: str = ""
    endpoint: str = ""
    keepalive: int = 25
    generate_key: bool = False


@router.get("/servers")
def list_servers(user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        return {"servers": [{"id": s.id, "name": s.name, "address": s.address,
                             "port": s.port, "enabled": s.enabled,
                             **wg.status_iface(s.name)}
                            for s in db.query(VpnServer).all()]}
    finally:
        db.close()


@router.post("/servers")
def create_server(body: ServerBody, user: dict = Depends(require_role("admin"))):
    try:
        clean = wg.validate_server(body.name, body.address, body.port)
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        keys = wg.genkeypair()
    except ValueError as e:
        raise HTTPException(500, f"wg absent ? {e}")
    db = get_session()
    try:
        if db.query(VpnServer).filter_by(name=clean["name"]).first():
            raise HTTPException(409, "serveur existe")
        s = VpnServer(private_key=keys["private_key"], enabled=True, **clean)
        db.add(s)
        db.commit()
        em.publish("config.updated", user["username"], f"vpn server+ {clean['name']}")
        return {"id": s.id, **clean, "public_key": keys["public_key"]}
    finally:
        db.close()


@router.get("/servers/{sid}/peers")
def list_peers(sid: int, user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        rows = db.query(VpnPeer).filter_by(server_id=sid).all()
        return {"peers": [{"id": p.id, "name": p.name, "public_key": p.public_key,
                          "allowed_ips": p.allowed_ips, "endpoint": p.endpoint,
                          "keepalive": p.keepalive} for p in rows]}
    finally:
        db.close()


@router.post("/servers/{sid}/peers")
def create_peer(sid: int, body: PeerBody, user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        srv = db.get(VpnServer, sid)
        if not srv:
            raise HTTPException(404, "serveur inconnu")
        pub = body.public_key
        if body.generate_key or not pub:
            try:
                pub = wg.genkeypair()["public_key"]
            except ValueError as e:
                raise HTTPException(500, f"wg absent ? {e}")
        try:
            clean = wg.validate_peer(body.name, pub, body.allowed_ips,
                                     body.endpoint, body.keepalive)
        except ValueError as e:
            raise HTTPException(400, str(e))
        p = VpnPeer(server_id=sid, preshared_key=body.preshared_key, **clean)
        db.add(p)
        db.commit()
        return {"id": p.id, **clean}
    finally:
        db.close()


@router.post("/servers/{sid}/apply")
def apply_server(sid: int, user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        srv = db.get(VpnServer, sid)
        if not srv:
            raise HTTPException(404, "serveur inconnu")
        peers = [{"name": p.name, "public_key": p.public_key,
                  "preshared_key": p.preshared_key, "allowed_ips": p.allowed_ips,
                  "endpoint": p.endpoint, "keepalive": p.keepalive}
                 for p in db.query(VpnPeer).filter_by(server_id=sid).all()]
        conf = {"name": srv.name, "address": srv.address, "port": srv.port,
                "private_key": srv.private_key}
    finally:
        db.close()
    path = wg.write_conf(srv.name, wg.render_conf(conf, peers))
    try:
        out = sm.control(f"wg-quick@{srv.name}", "restart", actor=user["username"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    em.publish("config.updated", user["username"], f"vpn apply {srv.name}")
    return {"conf": path, "service": out,
            "status": wg.status_iface(srv.name)}
