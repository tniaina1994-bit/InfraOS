# SPDX-License-Identifier: GPL-3.0-or-later
"""File Server Samba — partages (DB) -> smb.conf include + testparm + reload.

Permissions : valid users/groups (comptes InfraOS/AD), read only, guest.
ACL/Quota : champs stockes, enforcement phase 2 (setfacl/setquota documentes).
AD : security=ADS prevu (docs/FILESERVER.md), workgroup+realm en phase AD.
"""
from __future__ import annotations
import re
from pathlib import Path

SMB_INCLUDE = Path("/etc/samba/smb-infraos.conf")
SMB_CONF = Path("/etc/samba/smb.conf")
INCLUDE_LINE = "include = /etc/samba/smb-infraos.conf"
_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_ACL = re.compile(r"^[A-Za-z0-9_,.@ -]{0,255}$")


def validate_share(name: str, path: str, valid_users: str = "",
                   valid_groups: str = "") -> dict:
    if not _NAME.match(name or "") or name.lower() in ("global", "homes", "printers"):
        raise ValueError(f"nom de partage invalide ou reserve: {name}")
    p = (path or "").strip()
    if not p.startswith("/") or ".." in p or len(p) > 255:
        raise ValueError("chemin absolu requis (sans ..)")
    for k, v in (("valid_users", valid_users), ("valid_groups", valid_groups)):
        if v and not _ACL.match(v):
            raise ValueError(f"{k} invalide")
    return {"name": name, "path": p}


def render_shares(shares: list[dict]) -> str:
    out = ["# Genere par InfraOS — ne pas editer", ""]
    for sh in shares:
        if not sh.get("enabled", True):
            continue
        users = sh.get("valid_users", "") or None
        groups = ("@" + ", @".join(g.strip() for g in sh.get("valid_groups", "").split(",") if g.strip())
                  if sh.get("valid_groups") else None)
        vu = ", ".join(x for x in [users, groups] if x)
        out += [f"[{sh['name']}]",
                f"    path = {sh['path']}",
                f"    comment = {sh.get('comment') or sh['name']}",
                f"    read only = {'yes' if sh.get('read_only') else 'no'}",
                f"    browsable = {'yes' if sh.get('browsable', True) else 'no'}",
                f"    guest ok = {'yes' if sh.get('guest_ok') else 'no'}"]
        if vu:
            out.append(f"    valid users = {vu}")
        out.append("")
    return "\n".join(out)


def write_and_check(shares: list[dict]) -> dict:
    from .exec import run
    try:
        SMB_INCLUDE.parent.mkdir(parents=True, exist_ok=True)
        SMB_INCLUDE.write_text(render_shares(shares))
        current = SMB_CONF.read_text() if SMB_CONF.exists() else ""
        if INCLUDE_LINE not in current:
            Path(str(SMB_CONF) + ".infraos-bak").write_text(current)
            with open(SMB_CONF, "a") as f:
                f.write("\n" + INCLUDE_LINE + "\n")
    except OSError as e:
        return {"ok": False, "detail": f"ecriture impossible: {e}"}
    r = run("testparm", "-s", timeout=30, caller="shares.render")
    ok = r.rc == 0 and ("Loaded services file OK" in r.out or "Unknown" not in r.out)
    # testparm renvoie parfois rc != 0 pour warnings : verifie le marqueur OK
    if "Loaded services file OK" in r.out:
        ok = True
    return {"ok": ok, "detail": r.out[-2000:]}


def reload() -> dict:
    from .exec import run
    outs = []
    for svc in ("smbd", "nmbd"):
        r = run("systemctl", "restart", svc, timeout=60, caller="shares.reload")
        outs.append(f"{svc} rc={r.rc}")
    return {"detail": "; ".join(outs)}
