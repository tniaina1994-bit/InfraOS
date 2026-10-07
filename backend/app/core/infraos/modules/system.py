# SPDX-License-Identifier: GPL-3.0-or-later
"""System Module — etat hote du monolithe (lecture seule)."""
from __future__ import annotations
from ..module_base import InfraModule, ModuleStatus
from .. import system as sysinfo
from .. import packages as pkg


class SystemModule(InfraModule):
    name = "system"

    def status(self) -> ModuleStatus:
        info = sysinfo.os_info()
        upd = {"pending": 0}
        try:
            from ..updates import check_updates
            upd = check_updates()
        except Exception:
            pass
        running = True
        detail = f"{info.get('pretty', '?')} | virt={info.get('virt', '?')} | updates={upd.get('pending', '?')}"
        return ModuleStatus(name=self.name, installed=True, enabled=True,
                            running=running, detail=detail)

    def actions(self) -> list[str]:
        return ["info", "package"]

    def run_action(self, action: str, params: dict | None = None) -> dict:
        params = params or {}
        if action == "info":
            return sysinfo.os_info()
        if action == "package":
            name = str(params.get("name", ""))
            return pkg.is_installed(name)
        raise ValueError(f"action inconnue: {action}")
