# SPDX-License-Identifier: GPL-3.0-or-later
"""Identity & Domain — operations Samba AD (samba-tool, allow-list strict).

Toutes les entrees sont validees (regex) AVANT exec.run() ; argv construit
exclusivement par ce module (jamais de concatenation shell). Les mots de passe
passent par secret_args (audit masque) — jamais en base, jamais en clair.
Chaque ecriture est renvoyee telle quelle au routeur qui audit + events.
"""
from __future__ import annotations

import re

from .exec import ForbiddenCommand, run
from .identity_domain import is_provisioned

# noms AD : sAMAccountName / CN — sans caracteres speciaux LDAP
ACC_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
# groupes AD : espaces autorises (« Domain Admins », « Lab Admins »)
GROUP_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}$")
OU_CN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,64}$")
PASSWORD_MIN = 8

services_or_not = is_provisioned  # alias court


def _ensure() -> tuple[str, str]:
    """(realm, base_dn) si provisionne, sinon ValueError."""
    if not is_provisioned():
        raise ValueError("domaine non provisionne — creez d'abord le domaine")
    from .identity_domain import domain_row
    row = domain_row()
    realm = row.realm if row else ""
    if not realm:
        raise ValueError("domaine non enregistre en base")
    base_dn = "DC=" + ",DC=".join(realm.split("."))
    return realm, base_dn


def _maybe() -> tuple[str, str] | None:
    """Comme _ensure mais None si non provisionne (listes graceuses)."""
    try:
        return _ensure()
    except ValueError:
        return None


def _acc(name: str, field: str = "nom") -> str:
    name = (name or "").strip()
    rx = GROUP_RE if field == "groupe" else ACC_RE
    if not rx.match(name):
        raise ValueError(f"{field} invalide: {name!r}")
    return name


def _pw(pw: str) -> str:
    if not pw or len(pw) < PASSWORD_MIN:
        raise ValueError(f"mot de passe : {PASSWORD_MIN} caracteres minimum")
    if any(c in pw for c in "\n\r"):
        raise ValueError("mot de passe invalide")
    return pw


def _run(args: tuple[str, ...], timeout: int = 30, secret: tuple[str, ...] = (),
         caller: str = "identity.op") -> str:
    try:
        r = run("samba-tool", *args, timeout=timeout, caller=caller,
                secret_args=secret)
    except ForbiddenCommand as e:
        raise ValueError(f"commande refusee: {e}")
    if r.rc != 0:
        raise ValueError(f"samba-tool {args[0]} {args[1]}: {r.out[-400:]}")
    return r.out


def _parse_show(out: str) -> dict:
    d: dict = {}
    for line in out.splitlines():
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if k in d and d[k] != v:
            d[k] = f"{d[k]}, {v}"
        else:
            d[k] = v
    return d


def _uac_disabled(d: dict) -> bool:
    try:
        return bool(int(d.get("userAccountControl", "0")) & 0x2)
    except ValueError:
        return False


def _ou_dn(name: str, parent_dn: str, base_dn: str) -> str:
    """Construit un DN OU a partir d'un nom + parent (vide = racine domaine)."""
    name = (name or "").strip()
    if not OU_CN_RE.match(name):
        raise ValueError(f"nom d'OU invalide: {name!r}")
    if parent_dn:
        parent = parent_dn.strip()
        if not parent.upper().startswith("OU=") \
                or any(c in parent for c in ";|&$`\n\r"):
            raise ValueError(f"parent invalide: {parent_dn!r}")
        if not parent.upper().endswith(base_dn.upper()):
            raise ValueError(f"parent hors du domaine: {parent_dn!r}")
    else:
        parent = base_dn
    return f"OU={name},{parent}"


# ---------------------------------------------------------------- users ---

def list_users() -> dict:
    if not _maybe():
        return {"items": [], "count": 0, "detail": "domaine non provisionne"}
    out = _run(("user", "list"), timeout=30, caller="identity.users.list")
    names = sorted({ln.strip() for ln in out.splitlines() if ln.strip()})
    return {"items": [{"username": n} for n in names], "count": len(names)}


def get_user(name: str) -> dict:
    _ensure()
    name = _acc(name, "utilisateur")
    d = _parse_show(_run(("user", "show", name), caller="identity.users.show"))
    groups = _run(("user", "getgroups", name), caller="identity.users.groups").split()
    return {"username": name, "dn": d.get("dn", ""),
            "first_name": d.get("givenName", ""), "last_name": d.get("sn", ""),
            "email": d.get("mail", ""), "description": d.get("description", ""),
            "department": d.get("department", ""), "telephone": d.get("telephoneNumber", ""),
            "enabled": not _uac_disabled(d),
            "must_change_password": d.get("pwdLastSet", "") == "0",
            "groups": groups, "raw": {k: d[k] for k in
                                      ("sAMAccountName", "userAccountControl",
                                       "whenCreated", "pwdLastSet", "accountExpires",
                                       "lockoutTime") if k in d}}


def create_user(body: dict) -> dict:
    _ensure()
    name = _acc(body.get("username", ""), "utilisateur")
    pw = _pw(body.get("password", ""))
    args = ["user", "add", name, pw]
    for flag, key in (("--given-name=", "first_name"), ("--surname=", "last_name"),
                      ("--department=", "department"), ("--description=", "description"),
                      ("--telephone-number=", "telephone")):
        val = str(body.get(key) or "").strip()
        if val:
            if any(c in val for c in "\n\r;|&$`"):
                raise ValueError(f"caractere interdit dans {key}")
            args.append(flag + val)
    ou = str(body.get("ou") or "").strip()
    if ou:
        realm, base = _ensure()
        args.append("--userou=" + _ou_root(ou, base))
    if body.get("must_change_password", True):
        args.append("--must-change-at-next-login")
    _run(tuple(args), secret=(pw,), caller="identity.users.create")
    return {"username": name, "created": True}


def _ou_root(ou: str, base_dn: str) -> str:
    """--userou attend un DN SANS le domainDN : 'OU=Users' relatif."""
    ou = ou.strip()
    if not ou:
        raise ValueError("OU vide")
    if ou.upper().startswith("OU="):
        parts = [p.strip() for p in ou.split(",") if p.strip()]
        rel = [p for p in parts if p.upper().startswith("OU=")]
        if not rel:
            raise ValueError(f"OU invalide: {ou!r}")
        return ",".join(rel)
    if not OU_CN_RE.match(ou):
        raise ValueError(f"OU invalide: {ou!r}")
    return f"OU={ou}"


def update_user(name: str, body: dict) -> dict:
    """Edition AD limitee aux operations non interactives de samba-tool :
    deplacement, mot de passe, expiration. (champs profils = lecture seule v1)"""
    _ensure()
    name = _acc(name, "utilisateur")
    done = []
    target_ou = str(body.get("ou") or "").strip()
    if target_ou:
        _, base = _ensure()
        _run(("user", "move", name, _ou_dn_from_relative(target_ou, base)),
             caller="identity.users.move")
        done.append("deplace")
    if body.get("password"):
        set_password(name, body["password"],
                     must_change=bool(body.get("must_change_password", False)))
        done.append("mot de passe change")
    if "expiry_days" in body and body["expiry_days"] is not None:
        days = int(body["expiry_days"])
        if not 0 <= days <= 3650:
            raise ValueError("expiration : 0..3650 jours")
        if days == 0:
            _run(("user", "setexpiry", name, "--never"),
                 caller="identity.users.expiry")
        else:
            _run(("user", "setexpiry", name, f"--days={days}"),
                 caller="identity.users.expiry")
        done.append(f"expiration={days}j" if days else "expiration=jamais")
    if not done:
        raise ValueError("aucune modification (v1 : ou/password/expiry)")
    return {"username": name, "updated": done}


def _ou_dn_from_relative(rel: str, base_dn: str) -> str:
    """'OU=Users', 'OU=IT,OU=Users' ou 'Users' -> DN complet dans le domaine."""
    rel = (rel or "").strip()
    if not rel:
        raise ValueError("OU vide")
    parts = [p.strip() for p in rel.split(",") if p.strip()]
    norm = []
    for p in parts:
        if p.upper().startswith("OU="):
            cn = p[3:]
            dn_part = p
        elif "=" not in p and OU_CN_RE.match(p):
            cn, dn_part = p, f"OU={p}"
        else:
            raise ValueError(f"OU invalide: {p!r}")
        if not OU_CN_RE.match(cn):
            raise ValueError(f"OU invalide: {p!r}")
        norm.append(dn_part)
    dn = ",".join(norm)
    if not dn.upper().endswith(base_dn.upper()):
        dn = f"{dn},{base_dn}"
    return dn


def delete_user(name: str) -> dict:
    _ensure()
    name = _acc(name, "utilisateur")
    if name.lower() == "administrator":
        raise ValueError("le compte Administrator ne peut pas etre supprime")
    _run(("user", "delete", name), caller="identity.users.delete")
    return {"username": name, "deleted": True}


def enable_user(name: str, enabled: bool) -> dict:
    _ensure()
    name = _acc(name, "utilisateur")
    _run(("user", "enable" if enabled else "disable", name),
         caller="identity.users.enable" if enabled else "identity.users.disable")
    return {"username": name, "enabled": enabled}


def unlock_user(name: str) -> dict:
    _ensure()
    name = _acc(name, "utilisateur")
    _run(("user", "unlock", name), caller="identity.users.unlock")
    return {"username": name, "unlocked": True}


def set_password(name: str, password: str, must_change: bool = False) -> dict:
    _ensure()
    name = _acc(name, "utilisateur")
    pw = _pw(password)
    args = ["user", "setpassword", name, f"--newpassword={pw}"]
    if must_change:
        args.append("--must-change-at-next-login")
    _run(tuple(args), secret=(f"--newpassword={pw}",),
         caller="identity.users.password")
    return {"username": name, "password_set": True, "must_change": must_change}


def set_expiry(name: str, days: int) -> dict:
    _ensure()
    name = _acc(name, "utilisateur")
    days = int(days)
    if not 0 <= days <= 3650:
        raise ValueError("expiration : 0..3650 jours (0 = jamais)")
    if days == 0:
        _run(("user", "setexpiry", name, "--never"), caller="identity.users.expiry")
    else:
        _run(("user", "setexpiry", name, f"--days={days}"),
             caller="identity.users.expiry")
    return {"username": name, "expiry_days": days}


# --------------------------------------------------------------- groups ---

def list_groups() -> dict:
    if not _maybe():
        return {"items": [], "count": 0, "detail": "domaine non provisionne"}
    out = _run(("group", "list"), timeout=30, caller="identity.groups.list")
    names = sorted({ln.strip() for ln in out.splitlines() if ln.strip()})
    return {"items": [{"name": n} for n in names], "count": len(names)}


def get_group(name: str) -> dict:
    _ensure()
    name = _acc(name, "groupe")
    d = _parse_show(_run(("group", "show", name), caller="identity.groups.show"))
    members = [m.strip() for m in
               _run(("group", "listmembers", name), caller="identity.groups.members")
               .splitlines() if m.strip()]
    return {"name": name, "dn": d.get("dn", ""),
            "description": d.get("description", ""),
            "scope": d.get("groupType", ""), "members": members,
            "member_count": len(members)}


def create_group(body: dict) -> dict:
    _ensure()
    name = _acc(body.get("name", ""), "groupe")
    args = ["group", "add", name]
    desc = str(body.get("description") or "").strip()
    if desc:
        if any(c in desc for c in "\n\r;|&$`"):
            raise ValueError("caractere interdit dans description")
        args.append("--description=" + desc)
    _run(tuple(args), caller="identity.groups.create")
    return {"name": name, "created": True}


def delete_group(name: str) -> dict:
    _ensure()
    name = _acc(name, "groupe")
    protected = {"domain admins", "domain users", "domain computers",
                 "domain controllers", "enterprise admins", "schema admins",
                 "administrators", "guests", "krbtgt"}
    if name.lower() in protected:
        raise ValueError(f"groupe systeme protege: {name}")
    _run(("group", "delete", name), caller="identity.groups.delete")
    return {"name": name, "deleted": True}


def group_members(name: str, add: list[str] | None = None,
                  remove: list[str] | None = None) -> dict:
    _ensure()
    name = _acc(name, "groupe")
    add = [_acc(a, "membre") for a in (add or [])]
    remove = [_acc(r, "membre") for r in (remove or [])]
    if not add and not remove:
        raise ValueError("add ou remove requis")
    if add:
        _run(("group", "addmembers", name, ",".join(add)),
             caller="identity.groups.members")
    if remove:
        _run(("group", "removemembers", name, ",".join(remove)),
             caller="identity.groups.members")
    return {"group": name, "added": add, "removed": remove}


# ----------------------------------------------------------------- ous ---

def list_ous() -> dict:
    ctx = _maybe()
    if not ctx:
        return {"items": [], "count": 0, "detail": "domaine non provisionne"}
    _, base = ctx
    out = _run(("ou", "list"), timeout=30, caller="identity.ous.list")
    items = []
    for dn in (ln.strip() for ln in out.splitlines() if ln.strip()):
        cn = dn.split(",")[0][3:] if dn.upper().startswith("OU=") else dn
        parent = dn.split(",", 1)[1] if "," in dn else ""
        items.append({"dn": dn, "name": cn, "parent": parent,
                      "system": dn.upper() == base.upper()
                      or any(p in dn for p in ("CN=Users", "CN=Computers"))})
    return {"items": items, "count": len(items), "base_dn": base}


def create_ou(body: dict) -> dict:
    _, base = _ensure()
    name = (body.get("name") or "").strip()
    parent = (body.get("parent") or "").strip()
    dn = _ou_dn(name, parent, base)
    args = ["ou", "create", dn]
    desc = str(body.get("description") or "").strip()
    if desc:
        if any(c in desc for c in "\n\r;|&$`"):
            raise ValueError("caractere interdit dans description")
        args.append("--description=" + desc)
    _run(tuple(args), caller="identity.ous.create")
    return {"dn": dn, "created": True}


def delete_ou(dn: str, confirm: bool = False, force: bool = False) -> dict:
    _ensure()
    dn = _validate_dn(dn)
    objects = [o for o in _run(("ou", "listobjects", dn),
                               caller="identity.ous.listobjects").splitlines() if o.strip()]
    if not confirm:
        raise ValueError(f"confirm:true requis pour supprimer {dn} "
                         f"({len(objects)} objets)")
    if objects and not force:
        raise ValueError(f"OU non vide ({len(objects)} objets) — force:true requis")
    _run(("ou", "delete", dn), caller="identity.ous.delete")
    return {"dn": dn, "deleted": True, "objects_removed": len(objects)}


def move_object(dn: str, target_ou_dn: str, kind: str = "user") -> dict:
    _ensure()
    dn = _validate_dn(dn)
    target = _validate_dn(target_ou_dn)
    if kind == "user":
        name = dn.split(",")[0][3:]
        _run(("user", "move", name, target), caller="identity.ous.move")
    elif kind == "group":
        name = dn.split(",")[0][3:]
        _run(("group", "move", name, target), caller="identity.ous.move")
    elif kind == "computer":
        name = dn.split(",")[0][3:].rstrip("$")
        _run(("computer", "move", name, target), caller="identity.ous.move")
    elif kind == "ou":
        _run(("ou", "move", dn, target), caller="identity.ous.move")
    else:
        raise ValueError(f"type d'objet non supporte: {kind!r}")
    return {"object": dn, "target": target, "moved": True}


def rename_ou(old_dn: str, new_dn: str) -> dict:
    _ensure()
    old_dn, new_dn = _validate_dn(old_dn), _validate_dn(new_dn)
    _run(("ou", "rename", old_dn, new_dn), caller="identity.ous.rename")
    return {"old": old_dn, "new": new_dn, "renamed": True}


def _validate_dn(dn: str) -> str:
    dn = (dn or "").strip()
    if not dn or len(dn) > 512 or any(c in dn for c in ";|&$`\n\r"):
        raise ValueError(f"DN invalide: {dn!r}")
    for part in dn.split(","):
        p = part.strip()
        if not p or ":" in p:
            raise ValueError(f"DN invalide: {dn!r}")
        if p.upper().startswith(("OU=", "CN=", "DC=")):
            if not re.match(r"^[A-Za-z]+=[A-Za-z0-9 ._@-]+$", p):
                raise ValueError(f"DN invalide: {p!r}")
        elif "=" not in p:
            raise ValueError(f"DN invalide: {dn!r}")
    return dn


# ----------------------------------------------------------- computers ---

def list_computers() -> dict:
    if not _maybe():
        return {"items": [], "count": 0, "detail": "domaine non provisionne"}
    out = _run(("computer", "list"), timeout=30, caller="identity.computers.list")
    names = sorted({ln.strip() for ln in out.splitlines() if ln.strip()})
    return {"items": [{"name": n} for n in names], "count": len(names)}


def get_computer(name: str) -> dict:
    _ensure()
    name = _acc(name, "ordinateur")
    d = _parse_show(_run(("computer", "show", name), caller="identity.computers.show"))
    return {"name": name, "dn": d.get("dn", ""),
            "os": d.get("operatingSystem", ""), "ip": d.get("dNSHostName", ""),
            "description": d.get("description", ""),
            "enabled": not _uac_disabled(d),
            "last_logon": d.get("lastLogon", d.get("lastLogonTimestamp", "")),
            "raw": {k: d[k] for k in ("whenCreated", "userAccountControl",
                                      "operatingSystem", "dNSHostName") if k in d}}


def create_computer(body: dict) -> dict:
    _, base = _ensure()
    name = _acc(body.get("name", ""), "ordinateur").rstrip("$")
    args = ["computer", "add", name]
    ou = str(body.get("ou") or "").strip()
    if ou:
        args.append("--computerou=" + _ou_root(ou, base))
    desc = str(body.get("description") or "").strip()
    if desc:
        if any(c in desc for c in "\n\r;|&$`"):
            raise ValueError("caractere interdit dans description")
        args.append("--description=" + desc)
    _run(tuple(args), caller="identity.computers.create")
    return {"name": name, "created": True,
            "detail": "compte machine pre-cree — jointure Windows/Linux possible"}  # noqa


def delete_computer(name: str) -> dict:
    _ensure()
    name = _acc(name, "ordinateur")
    _run(("computer", "delete", name), caller="identity.computers.delete")
    return {"name": name, "deleted": True}


def set_computer_enabled(name: str, enabled: bool) -> dict:
    """Compte machine = principal AD : user enable/disable accepte <nom>$."""
    _ensure()
    name = _acc(name, "ordinateur")
    target = name if name.endswith("$") else name + "$"
    _run(("user", "enable" if enabled else "disable", target),
         caller="identity.computers.enable" if enabled else "identity.computers.disable")
    return {"name": name, "enabled": enabled}


# ------------------------------------------------------------ policies ---

_POLICY_FLAGS = {
    "complexity": (str, ("yes", "no")),
    "store_plaintext": (str, ("yes", "no")),
    "history_length": (int, (0, 24)),
    "min_pwd_length": (int, (0, 128)),
    "min_pwd_age": (int, (0, 998)),
    "max_pwd_age": (int, (0, 999)),
    "account_lockout_duration": (int, (0, 99999)),
    "account_lockout_threshold": (int, (0, 999)),
    "reset_account_lockout_after": (int, (0, 99999)),
}
_FLAG_CLI = {
    "complexity": "--complexity",
    "store_plaintext": "--store-plaintext",
    "history_length": "--history-length",
    "min_pwd_length": "--min-pwd-length",
    "min_pwd_age": "--min-pwd-age",
    "max_pwd_age": "--max-pwd-age",
    "account_lockout_duration": "--account-lockout-duration",
    "account_lockout_threshold": "--account-lockout-threshold",
    "reset_account_lockout_after": "--reset-account-lockout-after",
}


def get_password_policy() -> dict:
    if not _maybe():
        return {"detail": "domaine non provisionne", "settings": {}}
    out = _run(("domain", "passwordsettings", "show"), caller="identity.policy.show")
    settings: dict = {}
    for line in out.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            settings[k.strip()] = v.strip()
    return {"settings": settings}


def set_password_policy(body: dict) -> dict:
    """Spec §14 : applique la politique via Samba AD (pas seulement PostgreSQL)."""
    _ensure()
    args = ["domain", "passwordsettings", "set"]
    applied = {}
    for key, (typ, bounds) in _POLICY_FLAGS.items():
        if key not in body or body[key] is None:
            continue
        raw = body[key]
        if typ is str:
            val = str(raw).lower()
            if val not in bounds:
                raise ValueError(f"{key} : {'|'.join(bounds)}")
            args.append(f"{_FLAG_CLI[key]}={val}")
        else:
            try:
                ival = int(raw)
            except (TypeError, ValueError):
                raise ValueError(f"{key} : entier attendu")
            lo, hi = bounds
            if not lo <= ival <= hi:
                raise ValueError(f"{key} : {lo}..{hi}")
            args.append(f"{_FLAG_CLI[key]}={ival}")
        applied[key] = body[key]
    if not applied:
        raise ValueError("aucun parametre fourni")
    _run(tuple(args), timeout=30, caller="identity.policy.set")
    return {"applied": applied, "settings": get_password_policy().get("settings", {})}
