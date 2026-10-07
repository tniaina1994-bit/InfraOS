"""Identity & Domain Controller — API (§6-17, §26).

Lecture = operator+ ; ecritures/mutations = admin. Toute commande systeme
passe par exec.run() (allow-list), audit + events sur chaque mutation.
Pas de second systeme RBAC : deps.require_role() (roles rangs).
"""
from __future__ import annotations
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pydantic import BaseModel
from deps import require_role
from infraos import event_manager as em
from infraos import identity_domain as dom
from infraos import identity_samba as sm
from infraos import identity_health as hl

router = APIRouter()


def _ev(etype: str, actor: str, detail: str, result: str = "SUCCESS",
        resource: str = "") -> None:
    try:
        em.publish(etype, actor, detail, resource=resource, result=result)
    except Exception:
        pass


# ------------------------------------------------------------- synthese ---

@router.get("/status")
def status(user: dict = Depends(require_role("operator"))):
    return hl.domain_status()


@router.get("/domain")
def domain(user: dict = Depends(require_role("operator"))):
    try:
        return dom.domain_info()
    except ValueError as e:
        raise HTTPException(400, str(e))


# ------------------------------------------------------------ domain/wiz ---

class SetupBody(BaseModel):
    domain: str
    netbios: str = ""
    hostname: str = ""
    ip: str = ""
    admin_password: str = ""
    admin_user: str = "Administrator"
    dns_backend: str = "SAMBA_INTERNAL"
    stop_named: bool = True
    confirm: bool = False


@router.get("/domain/preflight")
def domain_preflight(domain: str = "", netbios: str = "", hostname: str = "",
                     ip: str = "", user: dict = Depends(require_role("operator"))):
    try:
        v = dom.validate_inputs(domain, netbios, hostname, ip)
        return dom.preflight(v)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/domain/setup")
def domain_setup(body: SetupBody, user: dict = Depends(require_role("admin"))):
    """§3 : provision du domaine (8 etapes) — admin + confirm explicite."""
    payload = body.model_dump()
    try:
        out = dom.setup(payload, actor=user["username"])
    except ValueError as e:
        _ev("identity.domain.setup", user["username"], f"setup KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.domain.setup", user["username"],
        f"setup {payload.get('domain')} status={out.get('status')}",
        result="SUCCESS" if out.get("status") in ("ready", "planned", "ok")
        else "FAILURE", resource=payload.get("domain", ""))
    return out


@router.post("/domain/backup")
def domain_backup(user: dict = Depends(require_role("admin"))):
    try:
        out = dom.backup(actor=user["username"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    _ev("identity.domain.backup", user["username"],
        f"backup {out.get('path', '')}", resource=out.get("path", ""))
    return out


@router.delete("/domain")
def domain_uninstall(confirm: bool = False,
                     user: dict = Depends(require_role("admin"))):
    """§29 : desinstallation avec garde (backup + confirm)."""
    try:
        out = dom.uninstall_guard(confirm, actor=user["username"])
    except ValueError as e:
        _ev("identity.domain.uninstall", user["username"], f"KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.domain.uninstall", user["username"],
        f"status={out.get('status')}")
    return out


# ------------------------------------------------------------- sante §20 ---

@router.get("/health")
def health(user: dict = Depends(require_role("operator"))):
    return hl.full_health()


@router.get("/domain/dns")
def domain_dns(user: dict = Depends(require_role("operator"))):
    return hl.domain_dns_health()


@router.get("/domain/kerberos")
def domain_kerberos(user: dict = Depends(require_role("operator"))):
    return hl.kerberos_info()


@router.get("/domain/ldap")
def domain_ldap(user: dict = Depends(require_role("operator"))):
    return hl.ldap_info()


@router.get("/domain/services")
def domain_services(user: dict = Depends(require_role("operator"))):
    return hl.services_status()


@router.get("/domain/time")
def domain_time(user: dict = Depends(require_role("operator"))):
    return hl.time_info()


@router.get("/domain/join")
def domain_join(user: dict = Depends(require_role("operator"))):
    return hl.join_info()


class KerberosTestBody(BaseModel):
    username: str
    password: str


@router.post("/test/kerberos")
def test_kerberos(body: KerberosTestBody, user: dict = Depends(require_role("admin"))):
    try:
        out = hl.kinit_test(body.username, body.password)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _ev("identity.test.kerberos", user["username"],
        f"kinit {body.username} -> {'OK' if out.get('success') else 'ECHEC'}",
        result="SUCCESS" if out.get("success") else "FAILURE")
    return out


@router.get("/test/dns")
def test_dns(name: str, rtype: str = "SRV",
             user: dict = Depends(require_role("operator"))):
    try:
        return hl.dns_query(name, rtype)
    except ValueError as e:
        raise HTTPException(400, str(e))


# --------------------------------------------------------------- users ---

class UserCreate(BaseModel):
    username: str
    password: str
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    description: str = ""
    department: str = ""
    telephone: str = ""
    ou: str = ""
    must_change_password: bool = True


class UserUpdate(BaseModel):
    ou: str = ""
    password: str = ""
    must_change_password: bool | None = None
    expiry_days: int | None = None


class PasswordBody(BaseModel):
    password: str
    must_change: bool = False


class ExpiryBody(BaseModel):
    days: int


class EnableBody(BaseModel):
    enabled: bool


@router.get("/users")
def list_users(user: dict = Depends(require_role("operator"))):
    return sm.list_users()


@router.get("/users/{name}")
def get_user(name: str, user: dict = Depends(require_role("operator"))):
    try:
        return sm.get_user(name)
    except ValueError as e:
        raise HTTPException(400 if "provision" in str(e) else 404, str(e))


@router.post("/users")
def create_user(body: UserCreate, user: dict = Depends(require_role("admin"))):
    try:
        out = sm.create_user(body.model_dump())
    except ValueError as e:
        _ev("identity.user.created", user["username"], f"{body.username} KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.user.created", user["username"], f"utilisateur {body.username}",
        resource=body.username)
    return out


@router.put("/users/{name}")
def update_user(name: str, body: UserUpdate,
                user: dict = Depends(require_role("admin"))):
    try:
        out = sm.update_user(name, body.model_dump())
    except ValueError as e:
        _ev("identity.user.updated", user["username"], f"{name} KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.user.updated", user["username"],
        f"{name}: {','.join(out.get('updated', []))}", resource=name)
    return out


@router.delete("/users/{name}")
def delete_user(name: str, user: dict = Depends(require_role("admin"))):
    try:
        out = sm.delete_user(name)
    except ValueError as e:
        _ev("identity.user.deleted", user["username"], f"{name} KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.user.deleted", user["username"], f"utilisateur {name}",
        resource=name)
    return out


@router.post("/users/{name}/enable")
def enable_user(name: str, user: dict = Depends(require_role("admin"))):
    try:
        out = sm.enable_user(name, True)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _ev("identity.user.enabled", user["username"], f"enable {name}", resource=name)
    return out


@router.post("/users/{name}/disable")
def disable_user(name: str, user: dict = Depends(require_role("admin"))):
    try:
        out = sm.enable_user(name, False)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _ev("identity.user.disabled", user["username"], f"disable {name}", resource=name)
    return out


@router.post("/users/{name}/unlock")
def unlock_user(name: str, user: dict = Depends(require_role("admin"))):
    try:
        out = sm.unlock_user(name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _ev("identity.user.unlocked", user["username"], f"unlock {name}", resource=name)
    return out


@router.post("/users/{name}/password")
def reset_password(name: str, body: PasswordBody,
                   user: dict = Depends(require_role("admin"))):
    try:
        out = sm.set_password(name, body.password, body.must_change)
    except ValueError as e:
        _ev("identity.user.password", user["username"], f"{name} KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.user.password", user["username"], f"reset mot de passe {name}",
        resource=name)
    return out


@router.post("/users/{name}/expiry")
def set_expiry(name: str, body: ExpiryBody,
               user: dict = Depends(require_role("admin"))):
    try:
        out = sm.set_expiry(name, body.days)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _ev("identity.user.updated", user["username"],
        f"expiration {name}={body.days}j", resource=name)
    return out


# -------------------------------------------------------------- groups ---

class GroupCreate(BaseModel):
    name: str
    description: str = ""


class MembersBody(BaseModel):
    add: list[str] = []
    remove: list[str] = []


@router.get("/groups")
def list_groups(user: dict = Depends(require_role("operator"))):
    return sm.list_groups()


@router.get("/groups/{name}")
def get_group(name: str, user: dict = Depends(require_role("operator"))):
    try:
        return sm.get_group(name)
    except ValueError as e:
        raise HTTPException(400 if "provision" in str(e) else 404, str(e))


@router.post("/groups")
def create_group(body: GroupCreate, user: dict = Depends(require_role("admin"))):
    try:
        out = sm.create_group(body.model_dump())
    except ValueError as e:
        _ev("identity.group.created", user["username"], f"{body.name} KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.group.created", user["username"], f"groupe {body.name}",
        resource=body.name)
    return out


@router.delete("/groups/{name}")
def delete_group(name: str, user: dict = Depends(require_role("admin"))):
    try:
        out = sm.delete_group(name)
    except ValueError as e:
        _ev("identity.group.deleted", user["username"], f"{name} KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.group.deleted", user["username"], f"groupe {name}", resource=name)
    return out


@router.post("/groups/{name}/members")
def group_members(name: str, body: MembersBody,
                  user: dict = Depends(require_role("admin"))):
    try:
        out = sm.group_members(name, body.add, body.remove)
    except ValueError as e:
        _ev("identity.group.members", user["username"], f"{name} KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.group.members", user["username"],
        f"{name} +{body.add} -{body.remove}", resource=name)
    return out


# ----------------------------------------------------------------- ous ---

class OuCreate(BaseModel):
    name: str
    parent: str = ""
    description: str = ""


class MoveBody(BaseModel):
    dn: str
    target: str
    kind: str = "user"


class RenameBody(BaseModel):
    old_dn: str
    new_dn: str


@router.get("/ous")
def list_ous(user: dict = Depends(require_role("operator"))):
    return sm.list_ous()


@router.post("/ous")
def create_ou(body: OuCreate, user: dict = Depends(require_role("admin"))):
    try:
        out = sm.create_ou(body.model_dump())
    except ValueError as e:
        _ev("identity.ou.created", user["username"], f"{body.name} KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.ou.created", user["username"], f"OU {out.get('dn')}",
        resource=out.get("dn", ""))
    return out


@router.delete("/ous")
def delete_ou(dn: str = Query(...), confirm: bool = False, force: bool = False,
              user: dict = Depends(require_role("admin"))):
    try:
        out = sm.delete_ou(dn, confirm, force)
    except ValueError as e:
        _ev("identity.ou.deleted", user["username"], f"{dn} KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.ou.deleted", user["username"], f"OU {dn}", resource=dn)
    return out


@router.post("/ous/move")
def move_object(body: MoveBody, user: dict = Depends(require_role("admin"))):
    try:
        out = sm.move_object(body.dn, body.target, body.kind)
    except ValueError as e:
        _ev("identity.ou.moved", user["username"], f"{body.dn} KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.ou.moved", user["username"],
        f"{body.dn} -> {body.target}", resource=body.dn)
    return out


@router.post("/ous/rename")
def rename_ou(body: RenameBody, user: dict = Depends(require_role("admin"))):
    try:
        out = sm.rename_ou(body.old_dn, body.new_dn)
    except ValueError as e:
        _ev("identity.ou.renamed", user["username"], f"{body.old_dn} KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.ou.renamed", user["username"],
        f"{body.old_dn} -> {body.new_dn}", resource=body.new_dn)
    return out


# ----------------------------------------------------------- computers ---

class ComputerCreate(BaseModel):
    name: str
    ou: str = ""
    description: str = ""


@router.get("/computers")
def list_computers(user: dict = Depends(require_role("operator"))):
    return sm.list_computers()


@router.get("/computers/{name}")
def get_computer(name: str, user: dict = Depends(require_role("operator"))):
    try:
        return sm.get_computer(name)
    except ValueError as e:
        raise HTTPException(400 if "provision" in str(e) else 404, str(e))


@router.post("/computers")
def create_computer(body: ComputerCreate,
                    user: dict = Depends(require_role("admin"))):
    try:
        out = sm.create_computer(body.model_dump())
    except ValueError as e:
        _ev("identity.computer.created", user["username"], f"{body.name} KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.computer.created", user["username"], f"PC {body.name}",
        resource=body.name)
    return out


@router.delete("/computers/{name}")
def delete_computer(name: str, user: dict = Depends(require_role("admin"))):
    try:
        out = sm.delete_computer(name)
    except ValueError as e:
        _ev("identity.computer.deleted", user["username"], f"{name} KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.computer.deleted", user["username"], f"PC {name}", resource=name)
    return out


@router.post("/computers/{name}/enable")
def enable_computer(name: str, user: dict = Depends(require_role("admin"))):
    try:
        out = sm.set_computer_enabled(name, True)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _ev("identity.computer.enabled", user["username"], f"enable {name}",
        resource=name)
    return out


@router.post("/computers/{name}/disable")
def disable_computer(name: str, user: dict = Depends(require_role("admin"))):
    try:
        out = sm.set_computer_enabled(name, False)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _ev("identity.computer.disabled", user["username"], f"disable {name}",
        resource=name)
    return out


# ------------------------------------------------------------ policies ---

class PolicyBody(BaseModel):
    complexity: str | None = None
    store_plaintext: str | None = None
    history_length: int | None = None
    min_pwd_length: int | None = None
    min_pwd_age: int | None = None
    max_pwd_age: int | None = None
    account_lockout_duration: int | None = None
    account_lockout_threshold: int | None = None
    reset_account_lockout_after: int | None = None


@router.get("/policies")
def get_policy(user: dict = Depends(require_role("operator"))):
    return sm.get_password_policy()


@router.put("/policies")
def set_policy(body: PolicyBody, user: dict = Depends(require_role("admin"))):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        out = sm.set_password_policy(data)
    except ValueError as e:
        _ev("identity.policy.changed", user["username"], f"KO: {e}",
            result="FAILURE")
        raise HTTPException(400, str(e))
    _ev("identity.policy.changed", user["username"],
        f"politique: {sorted(data)}")
    return out


# --------------------------------------------------------------- audit ---

@router.get("/audit")
def identity_audit(limit: int = 100,
                   user: dict = Depends(require_role("operator"))):
    """Audit des actions identity (AuditEvent, action LIKE 'identity.%')."""
    from infraos.db import get_session
    from infraos.models import AuditEvent
    session = get_session()
    try:
        rows = (session.query(AuditEvent)
                .filter(AuditEvent.action.like("identity.%"))
                .order_by(AuditEvent.id.desc())
                .limit(min(int(limit), 500)).all())
        return {"events": [{"ts": r.ts.isoformat() if r.ts else "",
                            "actor": r.actor, "action": r.action,
                            "detail": r.detail, "resource": r.resource,
                            "result": r.result}
                           for r in rows],
                "count": len(rows)}
    finally:
        session.close()
