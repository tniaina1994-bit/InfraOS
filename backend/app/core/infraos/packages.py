# SPDX-License-Identifier: GPL-3.0-or-later
"""Mecanismes natifs Debian/Linux — dpkg/apt (lecture seule, via exec)."""
from __future__ import annotations
import re
from .exec import run

_PKG = re.compile(r"^[a-z0-9][a-z0-9+.:~-]*$")


def is_installed(package: str) -> dict:
    if not _PKG.match(package or ""):
        raise ValueError("nom de paquet invalide")
    # `dpkg -l <pkg>` : ligne "ii ..." = installe (pas de $ dans argv, compatible allow-list)
    r = run("dpkg", "-l", package, caller="packages")
    installed = any(l.startswith("ii ") for l in r.out.splitlines())
    return {"package": package, "installed": installed, "detail": r.out[:200]}


def nft_ruleset() -> dict:
    """Lecture seule du firewall (degradee en LXC non-privilegie, normale sur ISO)."""
    r = run("nft", "list", "ruleset", caller="packages")
    return {"rc": r.rc, "ruleset": r.out[:8000],
            "detail": "LXC: peut etre vide (droits hotes)" if r.rc else "OK"}
