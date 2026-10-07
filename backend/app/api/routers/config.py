"""Configuration — lecture caviardée (operator+) et écriture validée (admin)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos import config_manager as cm
from deps import require_role

router = APIRouter()


class ConfigPatch(BaseModel):
    jwt_expire_min: int | None = None


@router.get("")
def get_config(user: dict = Depends(require_role("operator"))):
    return cm.show()


@router.put("")
def put_config(body: ConfigPatch, user: dict = Depends(require_role("admin"))):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        return cm.update(patch, actor=user["username"])
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/structure")
def get_structure(user: dict = Depends(require_role("operator"))):
    return cm.ensure_structure()


@router.get("/modules/{name}")
def get_module_config(name: str, user: dict = Depends(require_role("operator"))):
    try:
        return cm.module_config(name)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/modules/{name}")
def put_module_config(name: str, body: dict,
                      user: dict = Depends(require_role("admin"))):
    try:
        return cm.module_config(name, body)
    except ValueError as e:
        raise HTTPException(400, str(e))


class SecretBody(BaseModel):
    value: str


@router.post("/secrets/{name}")
def set_secret(name: str, body: SecretBody,
               user: dict = Depends(require_role("admin"))):
    try:
        return cm.set_secret(name, body.value)
    except ValueError as e:
        raise HTTPException(400, str(e))
