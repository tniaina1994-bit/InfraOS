# SPDX-License-Identifier: GPL-3.0-or-later
"""Network Module — interfaces, capacites firewall, ruleset (lecture seule)."""
from __future__ import annotations
from ..module_base import InfraModule, ModuleStatus
from .. import system as sysinfo
from ..detect import firewall_full_support
from .. import packages as pkg


class NetworkModule(InfraModule):
    name = "network"

    def status(self) -> ModuleStatus:
        ifaces = sysinfo.net_interfaces()
        ok, detail = firewall_full_support()
        ups = [i.get("name") for i in ifaces if i.get("up")]
        return ModuleStatus(name=self.name, installed=True, enabled=True,
                            running=bool(ups),
                            detail=f"interfaces up={ups} | firewall: {detail}")

    def actions(self) -> list[str]:
        return ["interfaces", "firewall", "ruleset"]

    def run_action(self, action: str, params: dict | None = None) -> dict:
        if action == "interfaces":
            return {"interfaces": sysinfo.net_interfaces()}
        if action == "firewall":
            ok, detail = firewall_full_support()
            return {"full_support": ok, "detail": detail}
        if action == "ruleset":
            return pkg.nft_ruleset()
        raise ValueError(f"action inconnue: {action}")
