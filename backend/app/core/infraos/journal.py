# SPDX-License-Identifier: GPL-3.0-or-later
"""Mecanismes natifs Debian/Linux — journald (lecture seule, via exec)."""
from __future__ import annotations
import re
from .exec import run

_SVC = re.compile(r"^[A-Za-z0-9@:_.-]+$")


def read_logs(service: str, lines: int = 50) -> dict:
    """Lit journald pour un service (nom valide depuis constante interne)."""
    if not _SVC.match(service or ""):
        raise ValueError("nom de service invalide")
    n = max(1, min(int(lines), 500))
    r = run("journalctl", "--no-pager", "-u", service, "-n", str(n),
            caller="journal")
    return {"service": service, "rc": r.rc, "logs": r.out[-8000:]}
