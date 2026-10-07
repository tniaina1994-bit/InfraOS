# SPDX-License-Identifier: GPL-3.0-or-later
"""Installation de paquets Debian — UNIQUEMENT via exec allow-list.

Garde-fous (philo securite):
- noms de paquets valides par regex Debian, jamais d'entree brute ;
- argv fixe ["install","-y","--no-install-recommends",...], shell=False ;
- la liste vient du manifest du module, jamais du Web directement ;
- RBAC admin + audit a l'appelant.
"""
from __future__ import annotations
import re
from .exec import run
from .logging_conf import get_logger

_PKG = re.compile(r"^[a-z0-9][a-z0-9+.:~-]*$")
log = get_logger("infraos.apt")


def install_packages(packages: list[str], caller: str = "module-manager") -> dict:
    clean = [p for p in packages if _PKG.match(p or "")]
    if len(clean) != len(packages):
        raise ValueError("nom de paquet invalide refuse")
    if not clean:
        return {"installed": [], "rc": 0, "detail": "rien a installer"}
    r = run("apt-get", "install", "-y", "--no-install-recommends", *clean,
            timeout=600, caller=caller)
    log.info("apt install %s rc=%s caller=%s", clean, r.rc, caller)
    return {"installed": clean, "rc": r.rc, "detail": r.out[-2000:]}


def remove_packages(packages: list[str], caller: str = "module-manager") -> dict:
    """Desinstallation (purge config) — memes garde-fous que l'installation."""
    clean = [p for p in packages if _PKG.match(p or "")]
    if len(clean) != len(packages):
        raise ValueError("nom de paquet invalide refuse")
    if not clean:
        return {"removed": [], "rc": 0, "detail": "rien a desinstaller"}
    r = run("apt-get", "remove", "-y", "--purge", *clean,
            timeout=600, caller=caller)
    log.info("apt remove %s rc=%s caller=%s", clean, r.rc, caller)
    return {"removed": clean, "rc": r.rc, "detail": r.out[-2000:]}
