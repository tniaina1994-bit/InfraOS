"""Auth locale (JWT) + endpoints d'etat des providers futurs (ldap/ad/kerberos)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.config import load_settings
from infraos.db import get_session
from infraos.security import create_token
from infraos import auth_providers
from infraos import event_manager as em
from deps import get_current_user

router = APIRouter()


class LoginBody(BaseModel):
    username: str
    password: str
    source: str = "local"  # local|ldap|ad|kerberos


@router.post("/login")
def login(body: LoginBody, request: Request):
    from ratelimit import check as _rl
    try:
        _rl(request)
    except HTTPException as e:
        try:
            em.publish("user.login", body.username, "rate limite",
                       resource="auth/login",
                       ip=request.client.host if request.client else "",
                       result="DENIED")
        except Exception:
            pass
        raise
    ip = request.client.host if request.client else ""
    s = load_settings()
    if body.source == "local":
        db = get_session()
        try:
            res = auth_providers.authenticate_local(body.username, body.password, db)
        except ValueError:
            try:
                em.publish("user.login", body.username, "mot de passe invalide",
                           resource="auth/login", ip=ip, result="FAILURE")
            except Exception:
                pass
            raise HTTPException(401, "identifiants invalides")
        finally:
            db.close()
        token = create_token(res.username, res.role, s.jwt_secret, s.jwt_expire_min)
        try:
            from infraos.security import decode_token as _dec
            from infraos import sessions as _sess
            _sess.register(res.username, _dec(token, s.jwt_secret)["jti"], s.jwt_expire_min)
        except Exception:
            pass
        try:
            em.publish("user.login", res.username, f"role={res.role}",
                       resource="auth/login", ip=ip, result="SUCCESS")
        except Exception:
            pass
        return {"access_token": token, "token_type": "bearer",
                "username": res.username, "role": res.role}
    # providers futurs: 501 documente si non configure
    try:
        fn = {"ldap": auth_providers.authenticate_ldap,
              "ad": auth_providers.authenticate_ad,
              "kerberos": auth_providers.authenticate_kerberos}[body.source]
    except KeyError:
        raise HTTPException(400, "source inconnue")
    try:
        fn(body.username, body.password, s)
    except auth_providers.NotConfigured as e:
        raise HTTPException(501, str(e))
    raise HTTPException(401, "echec")


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/logout")
def logout(user: dict = Depends(get_current_user)):
    from infraos import sessions as _sess
    _sess.revoke(user["username"], user.get("jti", ""))
    try:
        em.publish("user.logout", user["username"], "")
    except Exception:
        pass
    return {"revoked": True}


@router.get("/sessions")
def sessions(user: dict = Depends(get_current_user)):
    from infraos import sessions as _sess
    return {"sessions": _sess.list_for(user["username"])}


@router.delete("/sessions/{sid}")
def revoke_session(sid: int, user: dict = Depends(get_current_user)):
    from infraos.db import get_session as _gs
    from infraos.models import Session as _S
    db = _gs()
    try:
        row = db.get(_S, sid)
        if not row or (row.username != user["username"] and user.get("effective_role") != "admin"):
            raise HTTPException(404, "session inconnue")
        row.revoked = True
        db.commit()
        return {"revoked": True}
    finally:
        db.close()


@router.get("/providers")
def providers():
    """Etat des sources d'auth (local actif, autres prevus)."""
    s = load_settings()
    return {"providers": [
        {"name": "local", "status": "active"},
        {"name": "ldap", "status": "active" if s.ldap_url else "planned",
         "needs": "INFRAOS_LDAP_URL + INFRAOS_LDAP_BASE_DN"},
        {"name": "ad", "status": "active" if s.ad_domain else "planned",
         "needs": "INFRAOS_AD_DOMAIN (Samba/Winbind)"},
        {"name": "kerberos", "status": "active" if s.kerberos_realm else "planned",
         "needs": "INFRAOS_KERBEROS_REALM (kinit)"}]}
