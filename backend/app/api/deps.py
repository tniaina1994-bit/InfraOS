"""Dependances auth — JWT Bearer + RBAC (admin|operator|viewer)."""
from __future__ import annotations
import sys
from pathlib import Path
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.config import load_settings
from infraos.db import get_session
from infraos.models import User
from infraos.security import decode_token
from infraos import permissions as perm
from infraos import sessions as sess_mod

_bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if not creds:
        raise HTTPException(401, "token requis")
    s = load_settings()
    try:
        payload = decode_token(creds.credentials, s.jwt_secret)
    except ValueError as e:
        raise HTTPException(401, str(e))
    username, jti = payload.get("sub"), payload.get("jti", "")
    try:
        if not sess_mod.valid(username, jti):
            raise HTTPException(401, "session inconnue ou revoquee")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "session invalide")
    db = get_session()
    try:
        u = db.query(User).filter_by(username=username).first()
        if not u or u.disabled:
            raise HTTPException(401, "utilisateur inconnu ou desactive")
        eff = perm.effective_all(u.role, db, u.id)
        return {"username": u.username, "role": u.role,
                "effective_role": eff,
                "groups": [g.name for g in perm.user_groups(db, u.id)],
                "permissions": perm.permissions_for(eff), "jti": jti}
    finally:
        db.close()


def require_role(min_role: str):
    def _check(user: dict = Depends(get_current_user)) -> dict:
        if perm.RANK.get(user.get("effective_role", user["role"]), -1) < perm.RANK.get(min_role, 99):
            raise HTTPException(403, f"role {min_role} requis")
        return user
    return _check
