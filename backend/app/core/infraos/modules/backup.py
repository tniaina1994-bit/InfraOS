# SPDX-License-Identifier: GPL-3.0-or-later
"""Backup Manager — restic/borg (phase ulterieure : plans, destinations)."""
from ..module_base import SimpleServiceModule, ModuleStatus


class BackupModule(SimpleServiceModule):
    name = "backup"
    SERVICE = ""
    PACKAGE = ""
    PLANNED = ["plans", "runs"]

    def status(self) -> ModuleStatus:
        from .. import packages as pkg
        tools = {t: pkg.is_installed(t).get("installed", False)
                 for t in ("restic", "borgbackup")}
        inst = any(tools.values())
        return ModuleStatus(name=self.name, installed=inst, enabled=True,
                            running=False, detail=f"outils={tools} (aucun plan v1)")
