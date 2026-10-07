"""Roles & permissions — matrice, assignation (superadmin pour les roles)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.db import get_session
from infraos.models import User, Role, UserRole
from infraos import permissions as perm
from infraos import event_manager as em
from deps import require_role

router = APIRouter()
VALID_ROLES = ("superadmin", "admin", "operator", "readonly", "viewer")


class AssignBody(BaseModel):
    role: str


@router.get("")
def list_roles(user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        db_roles = {r.name: r for r in db.query(Role).all()}
        out = []
        for name in ("superadmin", "admin", "operator", "readonly"):
            r = db_roles.get(name)
            out.append({"name": name, "rank": r.rank if r else perm.RANK[name],
                        "permissions": perm.permissions_for(name),
                        "in_db": r is not None})
        return {"roles": out}
    finally:
        db.close()


@router.post("/users/{username}")
def assign_role(username: str, body: AssignBody,
                user: dict = Depends(require_role("superadmin"))):
    """Attribue un role DB supplementaire (superadmin uniquement)."""
    role = perm.canon(body.role)
    if role not in ("superadmin", "admin", "operator", "readonly"):
        raise HTTPException(400, "role invalide")
    db = get_session()
    try:
        u = db.query(User).filter_by(username=username).first()
        r = db.query(Role).filter_by(name=role).first()
        if not u or not r:
            raise HTTPException(404, "utilisateur ou role inconnu")
        if not db.query(UserRole).filter_by(user_id=u.id, role_id=r.id).first():
            db.add(UserRole(user_id=u.id, role_id=r.id))
            db.commit()
        em.publish("user.created", user["username"], f"role {role} -> {username}")
        return {"username": username, "role": role}
    finally:
        db.close()


@router.delete("/users/{username}/{role}")
def revoke_role(username: str, role: str,
                user: dict = Depends(require_role("superadmin"))):
    db = get_session()
    try:
        u = db.query(User).filter_by(username=username).first()
        r = db.query(Role).filter_by(name=perm.canon(role)).first()
        if not u or not r:
            raise HTTPException(404, "utilisateur ou role inconnu")
        if username == user["username"]:
            raise HTTPException(400, "auto-revocation interdite")
        db.query(UserRole).filter_by(user_id=u.id, role_id=r.id).delete()
        db.commit()
        return {"revoked": True}
    finally:
        db.close()
