# SPDX-License-Identifier: GPL-3.0-or-later
"""Providers d'authentification — local actif, AD/LDAP/Kerberos en stubs prevus.

Philo: commencer en local ; prevoir l'integration sans la bricoler :
chaque provider externe expose la meme interface et renvoie
NotConfigured tant que sa section config est vide.
"""
from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy.orm import Session
from .models import User
from .security import verify_password


class NotConfigured(Exception):
    pass


@dataclass
class AuthResult:
    username: str
    role: str
    source: str


def authenticate_local(username: str, password: str, session: Session) -> AuthResult:
    u = session.query(User).filter_by(username=username, auth_source="local").first()
    if not u or u.disabled or not verify_password(password, u.password_hash):
        raise ValueError("identifiants invalides")
    return AuthResult(username=u.username, role=u.role, source="local")


def authenticate_ldap(username: str, password: str, settings) -> AuthResult:
    """Stub phase 2 — necessite INFRAOS_LDAP_URL + INFRAOS_LDAP_BASE_DN."""
    if not getattr(settings, "ldap_url", "") or not getattr(settings, "ldap_base_dn", ""):
        raise NotConfigured("LDAP non configure (INFRAOS_LDAP_URL/BASE_DN vides)")
    raise NotConfigured("provider LDAP prevu phase 2 (python-ldap/sssd)")


def authenticate_ad(username: str, password: str, settings) -> AuthResult:
    """Stub phase 2 — necessite INFRAOS_AD_DOMAIN (jointure Samba/Winbind/sssd)."""
    if not getattr(settings, "ad_domain", ""):
        raise NotConfigured("AD non configure (INFRAOS_AD_DOMAIN vide)")
    raise NotConfigured("provider AD prevu phase 2 (Samba/Winbind)")


def authenticate_kerberos(username: str, password: str, settings) -> AuthResult:
    """Stub phase 2 — necessite INFRAOS_KERBEROS_REALM (kinit)."""
    if not getattr(settings, "kerberos_realm", ""):
        raise NotConfigured("Kerberos non configure (INFRAOS_KERBEROS_REALM vide)")
    raise NotConfigured("provider Kerberos prevu phase 2 (kinit)")
