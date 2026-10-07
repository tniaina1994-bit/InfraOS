# SPDX-License-Identifier: GPL-3.0-or-later
"""Permissions — roles initiaux (superadmin/admin/operator/readonly),
matrice code + miroir DB (roles/permissions/user_roles), role effectif.

Rang : readonly(0, alias viewer) < operator(1) < admin(2) < superadmin(3).
Effectif = max(colonne users.role, user_roles, roles des groupes).
"""
from __future__ import annotations

RANK = {"readonly": 0, "viewer": 0, "operator": 1, "admin": 2, "superadmin": 3}
CANONICAL = {"viewer": "readonly"}

PERMISSIONS: dict[str, set[str]] = {
    "readonly": {"dashboard:read", "system:read", "logs:read", "modules:read"},
    "operator": {"dashboard:read", "system:read", "logs:read", "modules:read",
                 "users:read", "groups:read", "modules:enable", "jobs:run",
                 "services:read", "events:read", "network:read", "updates:read",
                 # Identity & Domain (§26 — lecture)
                 "identity.read", "domain.read", "kerberos.read", "ldap.read",
                 "dns.read", "identity.audit.read", "users.read", "groups.read",
                 "computers.read", "ou.read", "identity.policy.read"},
    "admin": {"dashboard:read", "system:read", "logs:read", "modules:read",
              "users:read", "users:write", "groups:read", "groups:write",
              "modules:enable", "modules:install", "jobs:run",
              "services:read", "services:control", "config:read",
              "config:write", "events:read", "network:read", "network:manage",
              "firewall:read", "firewall:manage", "updates:read", "updates:manage",
              "dns:read", "dns:manage", "logs:manage",
              # Identity & Domain (§26 — ecritures)
              "identity.read", "domain.read", "kerberos.read", "ldap.read",
              "dns.read", "identity.audit.read", "users.read", "groups.read",
              "computers.read", "ou.read", "identity.policy.read",
              "identity.manage", "domain.manage", "users.create", "users.update",
              "users.delete", "users.disable", "users.reset_password",
              "groups.manage", "computers.manage", "ou.manage",
              "identity.policy.manage", "identity.test"},
    "superadmin": set(),  # rempli ci-dessous = admin + roles:manage
}
PERMISSIONS["superadmin"] = set(PERMISSIONS["admin"]) | {
    "roles:manage", "users:roles", "system:write"}


def canon(role: str) -> str:
    return CANONICAL.get(role, role)


def effective_role(user_role: str, group_roles: list[str]) -> str:
    best, best_rank = canon(user_role), RANK.get(canon(user_role), -1)
    for r in group_roles:
        rc, rk = canon(r), RANK.get(canon(r), -1)
        if rk > best_rank:
            best, best_rank = rc, rk
    return best


def permissions_for(role: str) -> list[str]:
    perms: set[str] = set()
    rank = RANK.get(canon(role), -1)
    for r, rrank in RANK.items():
        if r in CANONICAL or rrank <= rank:
            perms |= PERMISSIONS.get(canon(r), set())
    return sorted(perms)


def user_groups(session, user_id: int) -> list:
    from .models import UserGroup, Group
    rows = (session.query(Group).join(UserGroup, UserGroup.group_id == Group.id)
            .filter(UserGroup.user_id == user_id).all())
    return rows


def db_roles(session, user_id: int) -> list[str]:
    """Roles supplementaires via user_roles (DB)."""
    from .models import UserRole, Role
    return [r.name for r, _ in session.query(Role, UserRole)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(UserRole.user_id == user_id).all()]


def effective_all(user_role: str, session, user_id: int) -> str:
    groups = user_groups(session, user_id)
    roles = [canon(user_role)] + [canon(r) for r in db_roles(session, user_id)]
    roles += [canon(g.role) for g in groups]
    best, best_rank = "readonly", -1
    for r in roles:
        if RANK.get(r, -1) > best_rank:
            best, best_rank = r, RANK[r]
    return best


def seed_rbac(session) -> dict:
    """Seed idempotent des 4 roles + permissions + jointures."""
    from .models import Role, Permission, RolePermission
    for name, rank in (("readonly", 0), ("operator", 1), ("admin", 2), ("superadmin", 3)):
        if not session.query(Role).filter_by(name=name).first():
            session.add(Role(name=name, rank=rank,
                             description=f"role initial {name}"))
    session.commit()
    for role_name in ("readonly", "operator", "admin", "superadmin"):
        role = session.query(Role).filter_by(name=role_name).first()
        for pname in permissions_for(role_name):
            p = session.query(Permission).filter_by(name=pname).first()
            if not p:
                p = Permission(name=pname)
                session.add(p)
                session.commit()
            if not session.query(RolePermission).filter_by(
                    role_id=role.id, permission_id=p.id).first():
                session.add(RolePermission(role_id=role.id, permission_id=p.id))
    session.commit()
    return {"roles": 4,
            "permissions": session.query(Permission).count()}
