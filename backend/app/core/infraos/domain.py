# SPDX-License-Identifier: GPL-3.0-or-later
"""Domaine Windows/Linux — readiness Samba AD DC (lecture seule).

Philo: ne JAMAIS reimplementer Active Directory. On pilote Samba AD DC,
Kerberos et LDAP (paquets Debian). Le provisionnement se fait en CLI
(scripts/provision-ad.sh, bare-metal/VM) — jamais depuis le Web en v1.
"""
from __future__ import annotations
from . import packages as pkg
from .detect import detect_virt

AD_PORTS = [53, 88, 135, 137, 138, 139, 389, 445, 464, 636, 3268, 3269]
AD_PACKAGES = ["samba", "smbclient", "winbind", "krb5-user"]


def readiness() -> dict:
    virt = detect_virt()
    checks = []
    ok = True
    # LXC : deconseille pour un DC (ports, privileges, persistance)
    if virt == "lxc":
        checks.append({"check": "hyperviseur",
                       "status": "warn",
                       "detail": "LXC detecte : provisionnez l'AD sur ISO bare-metal/VM, pas ici"})
    else:
        checks.append({"check": "hyperviseur", "status": "ok",
                       "detail": f"virt={virt}"})
    missing = [p for p in AD_PACKAGES
               if not pkg.is_installed(p).get("installed")]
    checks.append({"check": "paquets", "status": "ok" if not missing else "fail",
                   "detail": "tous presents" if not missing else f"manquants: {missing}"})
    if missing:
        ok = False
    # ports d'ecoute AD (via /proc, sans nmap)
    listening = set()
    try:
        with open("/proc/net/tcp") as f:
            for line in f.read().splitlines()[1:]:
                parts = line.split()
                if len(parts) > 3 and parts[3] == "0A":
                    listening.add(int(parts[1].split(":")[1], 16))
    except OSError:
        pass
    busy = [p for p in AD_PORTS if p in listening]
    checks.append({"check": "ports", "status": "ok" if not busy else "warn",
                   "detail": "libres" if not busy else f"occupes: {busy}"})
    # deja provisionne ?
    import os
    provisioned = os.path.exists("/var/lib/samba/private/sam.ldb")
    checks.append({"check": "provision", "status": "ok" if provisioned else "planned",
                   "detail": "sam.ldb present" if provisioned else
                             "non provisionne (scripts/provision-ad.sh en CLI)"})
    return {"ready": ok and not busy, "provisioned": provisioned,
            "checks": checks,
            "strategy": "Samba AD DC + Kerberos + LDAP (Debian natif, pas de reimplementation)"}
