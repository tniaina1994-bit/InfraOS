"""Firewall nftables — CRUD FirewallRule + apply (admin, check avant apply)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.db import get_session
from infraos.models import FirewallRule
from infraos import nft
from infraos import event_manager as em
from deps import require_role

router = APIRouter()


class RuleBody(BaseModel):
    name: str = "rule"
    chain: str = "input"
    action: str = "accept"
    proto: str = "all"
    src: str = ""
    dst: str = ""
    dport: int = 0
    in_if: str = ""
    out_if: str = ""
    nat_to: str = ""
    log: bool = False
    position: int = 100
    enabled: bool = True


def _out(r) -> dict:
    return {"id": r.id, "name": r.name, "chain": r.chain, "action": r.action,
            "proto": r.proto, "src": r.src, "dst": r.dst, "dport": r.dport,
            "in_if": r.in_if, "out_if": r.out_if, "nat_to": r.nat_to,
            "log": r.log, "position": r.position, "enabled": r.enabled}


@router.get("/rules")
def list_rules(user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        rows = db.query(FirewallRule).order_by(FirewallRule.position).all()
        return {"rules": [_out(r) for r in rows]}
    finally:
        db.close()


@router.post("/rules")
def create_rule(body: RuleBody, user: dict = Depends(require_role("admin"))):
    try:
        clean = nft.validate_rule(body.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))
    db = get_session()
    try:
        r = FirewallRule(**clean)
        db.add(r)
        db.commit()
        return _out(r)
    finally:
        db.close()


@router.delete("/rules/{rid}")
def delete_rule(rid: int, user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        r = db.get(FirewallRule, rid)
        if not r:
            raise HTTPException(404, "regle inconnue")
        db.delete(r)
        db.commit()
        return {"deleted": rid}
    finally:
        db.close()


@router.get("/preview")
def preview(user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        rows = db.query(FirewallRule).all()
        rules = [{"name": r.name, "chain": r.chain, "action": r.action,
                  "proto": r.proto, "src": r.src, "dst": r.dst, "dport": r.dport,
                  "in_if": r.in_if, "out_if": r.out_if, "nat_to": r.nat_to,
                  "log": r.log, "position": r.position, "enabled": r.enabled}
                 for r in rows]
        return {"ruleset": nft.render(rules)}
    finally:
        db.close()


@router.post("/apply")
def apply(user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        rows = db.query(FirewallRule).all()
        rules = [{"name": r.name, "chain": r.chain, "action": r.action,
                  "proto": r.proto, "src": r.src, "dst": r.dst, "dport": r.dport,
                  "in_if": r.in_if, "out_if": r.out_if, "nat_to": r.nat_to,
                  "log": r.log, "position": r.position, "enabled": r.enabled}
                 for r in rows]
    finally:
        db.close()
    try:
        ruleset = nft.render(rules)
    except ValueError as e:
        raise HTTPException(400, str(e))
    out = nft.apply(ruleset)
    em.publish("config.updated", user["username"], f"firewall apply={out.get('applied')}")
    return out
