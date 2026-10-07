# SPDX-License-Identifier: GPL-3.0-or-later
"""Etat des modules — persistant dans data_dir/modules.json (0600).

Survit aux reboots et mises a jour (philo: configuration persistante).
"""
from __future__ import annotations
import json
import os
from pathlib import Path

DEFAULTS = {"enabled": True}


def _path(data_dir: str | None = None) -> Path:
    if data_dir:
        return Path(data_dir) / "modules.json"
    try:
        from .config import load_settings
        return Path(load_settings().data_dir) / "modules.json"
    except Exception:
        return Path(os.getenv("INFRAOS_DATA_DIR", "/var/lib/infraos")) / "modules.json"


def load(data_dir: str | None = None) -> dict:
    p = _path(data_dir)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (OSError, ValueError):
            return {}
    return {}


def save(state: dict, data_dir: str | None = None) -> None:
    p = _path(data_dir)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, indent=1))
        os.chmod(p, 0o600)
    except OSError:
        pass


def is_enabled(name: str, data_dir: str | None = None, default: bool = True) -> bool:
    return load(data_dir).get(name, {"enabled": default})["enabled"]


def set_enabled(name: str, enabled: bool, data_dir: str | None = None) -> None:
    st = load(data_dir)
    st[name] = {"enabled": enabled}
    save(st, data_dir)
