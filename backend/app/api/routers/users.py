"""Utilisateurs — DB InfraOS (RBAC) + comptes systeme (lecture seule)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.db import get_session
from infraos.models import User
from infraos.config import load_settings
from infraos.security import hash_password, verify_password
from infraos import password_policy as policy
from infraos import permissions as perm
from infraos import event_manager as em
from deps import require_role, get_current_user

router = APIRouter()
try:
    import pwd as _pwd
except ImportError:
    _pwd = None


class CreateUser(BaseModel):
    username: str
    password: str
    role: str = "viewer"
    display_name: str = ""


@router.get("")
def list_users_db(user: dict = Depends(require_role("operator"))):
    db = get_session()
    try:
        rows = db.query(User).all()
        out = []
        for u in rows:
            groups = perm.user_groups(db, u.id)
            out.append({"username": u.username, "role": u.role,
                        "effective_role": perm.effective_all(u.role, db, u.id),
                        "groups": [g.name for g in groups],
                        "source": u.auth_source, "disabled": u.disabled})
        return {"users": out, "count": len(out)}
    finally:
        db.close()


def _enforce_policy(password: str):
    s = load_settings()
    try:
        policy.check_password(password, s.password_min_length, s.password_require_digit)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("")
def create_user(body: CreateUser, user: dict = Depends(require_role("admin"))):
    if perm.canon(body.role) not in ("superadmin", "admin", "operator", "readonly", "viewer"):
        raise HTTPException(400, "role invalide")
    # on ne peut pas attribuer un rang >= au sien (sauf superadmin qui peut tout)
    me_rank = perm.RANK.get(user.get("effective_role", user["role"]), -1)
    want_rank = perm.RANK.get(perm.canon(body.role), 99)
    if want_rank >= me_rank and user.get("effective_role") != "superadmin":
        raise HTTPException(403, "attribution de ce role reservee au superadmin")
    if not body.username or len(body.username) < 3 or len(body.username) > 64:
        raise HTTPException(400, "nom d'utilisateur invalide")
    _enforce_policy(body.password)
    db = get_session()
    try:
        if db.query(User).filter_by(username=body.username).first():
            raise HTTPException(409, "utilisateur existe")
        u = User(username=body.username, password_hash=hash_password(body.password),
                 role=body.role, display_name=body.display_name)
        db.add(u)
        db.commit()
        try:
            em.publish("user.created", user["username"], f"{body.username} role={body.role}")
        except Exception:
            pass
        return {"username": u.username, "role": u.role}
    finally:
        db.close()


@router.get("/system")
def list_system_users(user: dict = Depends(require_role("operator"))):
    """Comptes OS natifs (lecture seule) — distinct des comptes InfraOS (DB)."""
    if _pwd is None:
        return {"users": [], "count": 0}
    out = [{"name": p.pw_name, "uid": p.pw_uid, "home": p.pw_dir}
           for p in _pwd.getpwall() if p.pw_uid >= 1000 or p.pw_name == "root"]
    return {"users": out, "count": len(out)}


class PasswordBody(BaseModel):
    current_password: str = ""
    new_password: str = ""


@router.post("/me/password")
def change_own_password(body: PasswordBody, user: dict = Depends(get_current_user)):
    _enforce_policy(body.new_password)
    db = get_session()
    try:
        u = db.query(User).filter_by(username=user["username"]).first()
        if not u or not verify_password(body.current_password, u.password_hash):
            raise HTTPException(401, "mot de passe actuel invalide")
        u.password_hash = hash_password(body.new_password)
        # revoque les autres sessions (garde la courante)
        from infraos.models import Session as _S
        for row in db.query(_S).filter_by(username=u.username).all():
            if row.jti != user.get("jti"):
                row.revoked = True
        db.commit()
        em.publish("user.password", u.username, "self-change")
        return {"changed": True}
    finally:
        db.close()


@router.post("/{username}/disable")
def disable_user(username: str, user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        u = db.query(User).filter_by(username=username).first()
        if not u:
            raise HTTPException(404, "utilisateur inconnu")
        if username == user["username"]:
            raise HTTPException(400, "auto-desactivation interdite")
        u.disabled = True
        db.commit()
        em.publish("user.disabled", user["username"], username)
        return {"username": username, "disabled": True}
    finally:
        db.close()


@router.post("/{username}/enable")
def enable_user(username: str, user: dict = Depends(require_role("admin"))):
    db = get_session()
    try:
        u = db.query(User).filter_by(username=username).first()
        if not u:
            raise HTTPException(404, "utilisateur inconnu")
        u.disabled = False
        db.commit()
        return {"username": username, "disabled": False}
    finally:
        db.close()


@router.get("/me/permissions")
def my_permissions(user: dict = Depends(get_current_user)):
    return {"username": user["username"], "role": user["role"],
            "effective_role": user.get("effective_role", user["role"]),
            "groups": user.get("groups", []),
            "permissions": user.get("permissions", [])}
