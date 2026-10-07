"""Groupes — CRUD admin, membres, lecture operator+."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.db import get_session
from infraos.models import User, Group, UserGroup
from infraos import permissions as perm
from infraos import event_manager as em
from deps import require_role

router = APIRouter()


class GroupBody(BaseModel):
    name: str
    description: str = ""
    role: str = "viewer"


class MemberBody(BaseModel):
    username: str


@router.get("")
def list_groups(user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        rows = db.query(Group).all()
        out = []
        for g in rows:
            n = db.query(UserGroup).filter_by(group_id=g.id).count()
            out.append({"name": g.name, "description": g.description,
                        "role": g.role, "members": n})
        return {"groups": out, "count": len(out)}
    finally:
        db.close()


@router.post("")
def create_group(body: GroupBody, user: dict = Depends(require_role("admin"))):
    if not body.name or len(body.name) > 64:
        raise HTTPException(400, "nom de groupe invalide")
    if body.role not in ("admin", "operator", "viewer"):
        raise HTTPException(400, "role invalide")
    db = get_session()
    try:
        if db.query(Group).filter_by(name=body.name).first():
            raise HTTPException(409, "groupe existe")
        db.add(Group(name=body.name, description=body.description, role=body.role))
        db.commit()
        em.publish("group.created", user["username"], body.name)
        return {"name": body.name, "role": body.role}
    finally:
        db.close()


@router.post("/{name}/members")
def add_member(name: str, body: MemberBody, user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        g = db.query(Group).filter_by(name=name).first()
        u = db.query(User).filter_by(username=body.username).first()
        if not g or not u:
            raise HTTPException(404, "groupe ou utilisateur inconnu")
        if not db.query(UserGroup).filter_by(user_id=u.id, group_id=g.id).first():
            db.add(UserGroup(user_id=u.id, group_id=g.id))
            db.commit()
        em.publish("group.member", user["username"], f"{body.username} -> {name}")
        eff = perm.effective_role(u.role, [x.role for x in perm.user_groups(db, u.id)])
        return {"group": name, "username": body.username, "effective_role": eff}
    finally:
        db.close()


@router.delete("/{name}/members/{username}")
def del_member(name: str, username: str, user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        g = db.query(Group).filter_by(name=name).first()
        u = db.query(User).filter_by(username=username).first()
        if not g or not u:
            raise HTTPException(404, "groupe ou utilisateur inconnu")
        db.query(UserGroup).filter_by(user_id=u.id, group_id=g.id).delete()
        db.commit()
        return {"removed": True}
    finally:
        db.close()
