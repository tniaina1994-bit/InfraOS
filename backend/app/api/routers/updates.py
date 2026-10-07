"""Mises a jour — apt/dpkg comme base (jamais remplaces).

Lecture (operator+) : check, list, security-only, package info, history.
Installation (admin) : liste explicite de paquets, auditee + historisee.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos import updates as um
from infraos import event_manager as em
from deps import require_role

router = APIRouter()

@router.get("")
def updates_status():
    return um.check_updates()


@router.get("/list")
def updates_list(user: dict = Depends(require_role("operator"))):
    return um.list_updates()


@router.get("/security")
def updates_security(user: dict = Depends(require_role("operator"))):
    return um.security_updates()


@router.get("/package")
def package_info(name: str, user: dict = Depends(require_role("operator"))):
    try:
        return um.package_info(name)
    except ValueError as e:
        raise HTTPException(400, str(e))


class InstallBody(BaseModel):
    packages: list[str] = []
    kind: str = "packages"


@router.post("/install")
def install_updates(body: InstallBody, user: dict = Depends(require_role("admin"))):
    try:
        out = um.install_updates(body.packages, actor=user["username"], kind=body.kind)
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        em.publish("config.updated", user["username"],
                   f"updates install {len(body.packages)} pkgs {out['status']}")
    except Exception:
        pass
    return out


@router.get("/history")
def updates_history(limit: int = 20, user: dict = Depends(require_role("operator"))):
    return {"runs": um.history(limit)}


@router.get("/sources")
def list_sources(user: dict = Depends(require_role("operator"))):
    return {"sources": um.list_sources()}


class SourceBody(BaseModel):
    name: str
    url: str
    suite: str = ""
    components: str = "main"
    key_url: str = ""


@router.post("/sources")
def add_source(body: SourceBody, user: dict = Depends(require_role("admin"))):
    try:
        out = um.add_source(body.name, body.url, body.suite,
                            body.components, body.key_url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        em.publish("config.updated", user["username"], f"apt source add {out['name']}")
    except Exception:
        pass
    return out


@router.delete("/sources/{name}")
def delete_source(name: str, user: dict = Depends(require_role("admin"))):
    try:
        out = um.remove_source(name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        em.publish("config.updated", user["username"], f"apt source remove {name}")
    except Exception:
        pass
    return out


@router.post("/full-upgrade")
def full_upgrade(user: dict = Depends(require_role("admin"))):
    """apt update + full-upgrade — admin uniquement, audite + historise."""
    try:
        return um.full_upgrade(actor=user["username"])
    except ValueError as e:
        raise HTTPException(400, str(e))
