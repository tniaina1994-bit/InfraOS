"""File Server Samba — CRUD partages + testparm + reload (admin ecritures)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.db import get_session
from infraos.models import SambaShare
from infraos import fileserver as smb
from infraos import event_manager as em
from deps import require_role

router = APIRouter()


class ShareBody(BaseModel):
    name: str
    path: str
    comment: str = ""
    read_only: bool = False
    browsable: bool = True
    guest_ok: bool = False
    valid_users: str = ""
    valid_groups: str = ""
    enabled: bool = True


def _out(s) -> dict:
    return {"id": s.id, "name": s.name, "path": s.path, "comment": s.comment,
            "read_only": s.read_only, "browsable": s.browsable,
            "guest_ok": s.guest_ok, "valid_users": s.valid_users,
            "valid_groups": s.valid_groups, "enabled": s.enabled}


@router.get("/shares")
def list_shares(user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        return {"shares": [_out(s) for s in db.query(SambaShare).all()]}
    finally:
        db.close()


@router.post("/shares")
def create_share(body: ShareBody, user: dict = Depends(require_role("admin"))):
    try:
        smb.validate_share(body.name, body.path, body.valid_users, body.valid_groups)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db = get_session()
    try:
        if db.query(SambaShare).filter_by(name=body.name).first():
            raise HTTPException(409, "partage existe")
        s = SambaShare(**body.model_dump())
        db.add(s)
        db.commit()
        Path(body.path).mkdir(parents=True, exist_ok=True)
        em.publish("config.updated", user["username"], f"share+ {body.name}")
        return _out(s)
    finally:
        db.close()


@router.delete("/shares/{sid}")
def delete_share(sid: int, user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        s = db.get(SambaShare, sid)
        if not s:
            raise HTTPException(404, "partage inconnu")
        db.delete(s)
        db.commit()
        return {"deleted": sid}
    finally:
        db.close()


@router.post("/apply")
def apply(user: dict = Depends(require_role("admin"))):
    from pathlib import Path as _P
    db = get_session()
    try:
        shares = [{"name": s.name, "path": s.path, "comment": s.comment,
                   "read_only": s.read_only, "browsable": s.browsable,
                   "guest_ok": s.guest_ok, "valid_users": s.valid_users,
                   "valid_groups": s.valid_groups, "enabled": s.enabled}
                  for s in db.query(SambaShare).all()]
    finally:
        db.close()
    res = smb.write_and_check(shares)
    if not res["ok"]:
        return {"applied": False, "stage": "testparm", **res}
    rel = smb.reload()
    em.publish("config.updated", user["username"], "shares apply")
    return {"applied": True, "stage": "reload", **rel}
