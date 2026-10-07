"""Reseau — lecture (publique/dev) + ecriture stagee protegee (admin)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.system import net_interfaces
from infraos.detect import detect_virt, firewall_full_support
from infraos import netconfig as nc
from infraos import event_manager as em
from deps import require_role

router = APIRouter()

@router.get("/interfaces")
def interfaces():
    return {"virt": detect_virt(), "interfaces": net_interfaces()}

@router.get("/firewall-capabilities")
def fw_caps():
    ok, msg = firewall_full_support()
    return {"full_support": ok, "detail": msg}


@router.get("/routes")
def routes(user: dict = Depends(require_role("operator"))):
    return {"routes": nc.routes(), "gateways": nc.gateways()}


@router.get("/dns-resolver")
def resolver(user: dict = Depends(require_role("operator"))):
    return nc.dns_resolver()


class StaticBody(BaseModel):
    interface: str
    cidr: str
    gateway: str = ""
    confirm: bool = False


class VlanBody(BaseModel):
    interface: str
    vlan_id: int
    cidr: str = ""
    confirm: bool = False


@router.post("/static")
def static_ip(body: StaticBody, user: dict = Depends(require_role("admin"))):
    import socket
    try:
        out = nc.static_address(body.interface, body.cidr, body.gateway,
                                body.confirm, current_iface="")
    except ValueError as e:
        raise HTTPException(400, str(e))
    em.publish("config.updated", user["username"], f"net static {body.interface} {body.cidr}")
    return out


@router.post("/vlan")
def create_vlan(body: VlanBody, user: dict = Depends(require_role("admin"))):
    try:
        out = nc.vlan(body.interface, body.vlan_id, body.cidr, body.confirm)
    except ValueError as e:
        raise HTTPException(400, str(e))
    em.publish("config.updated", user["username"], f"net vlan {body.interface}.{body.vlan_id}")
    return out


class DhcpBody(BaseModel):
    interface: str
    confirm: bool = False


@router.post("/dhcp")
def dhcp_ip(body: DhcpBody, user: dict = Depends(require_role("admin"))):
    """Stage DHCP (DHCP=yes) pour une interface — admin, audite."""
    try:
        out = nc.dhcp_address(body.interface, body.confirm, current_iface="")
    except ValueError as e:
        raise HTTPException(400, str(e))
    em.publish("config.updated", user["username"], f"net dhcp {body.interface}")
    return out


@router.get("/config/{iface}")
def staged_config(iface: str, user: dict = Depends(require_role("operator"))):
    """Config stagee InfraOS (statique/dhcp) — prefill du formulaire."""
    try:
        return nc.staged_config(iface)
    except ValueError as e:
        raise HTTPException(400, str(e))


class LinkBody(BaseModel):
    interface: str
    up: bool


@router.post("/link")
def set_link(body: LinkBody, user: dict = Depends(require_role("admin"))):
    """Monte/une une interface (ip link set — allow-list exec)."""
    try:
        out = nc.link_set(body.interface, body.up)
    except ValueError as e:
        raise HTTPException(400, str(e))
    em.publish("config.updated", user["username"],
               f"net link {body.interface} {'up' if body.up else 'down'}")
    return out


class BridgeBody(BaseModel):
    name: str
    cidr: str = ""
    confirm: bool = False


@router.post("/bridge")
def create_bridge(body: BridgeBody, user: dict = Depends(require_role("admin"))):
    try:
        out = nc.bridge(body.name, body.cidr, body.confirm)
    except ValueError as e:
        raise HTTPException(400, str(e))
    em.publish("config.updated", user["username"], f"net bridge {body.name}")
    return out


@router.delete("/interface/{name}")
def remove_interface(name: str, confirm: bool = False, apply: bool = False,
                     user: dict = Depends(require_role("admin"))):
    """Supprime la configuration InfraOS d'une interface/VLAN/bridge."""
    try:
        out = nc.remove_config(name, confirm=confirm, apply=apply)
    except ValueError as e:
        raise HTTPException(400, str(e))
    em.publish("config.updated", user["username"], f"net config remove {name}")
    return out
