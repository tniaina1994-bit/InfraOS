# SPDX-License-Identifier: GPL-3.0-or-later
"""Update Manager — APT natif (v1: releve ; phase ulterieure : planifier)."""
from ..module_base import SimpleServiceModule, ModuleStatus


class UpdateModule(SimpleServiceModule):
    name = "updates"
    SERVICE = ""
    PACKAGE = "apt"
    PLANNED = ["schedule"]

    def status(self) -> ModuleStatus:
        try:
            from ..updates import check_updates
            n = check_updates().get("pending", 0)
            return ModuleStatus(name=self.name, installed=True, enabled=True,
                                running=True, detail=f"{n} mises a jour en attente (APT)")
        except Exception as e:
            return ModuleStatus(name=self.name, installed=True, enabled=True,
                                running=False, detail=str(e)[:200])
