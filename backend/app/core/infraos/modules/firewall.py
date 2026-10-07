# SPDX-License-Identifier: GPL-3.0-or-later
"""Firewall Manager — nftables (phase ulterieure : zones, regles, NAT)."""
from ..module_base import SimpleServiceModule


class FirewallModule(SimpleServiceModule):
    name = "firewall"
    SERVICE = "nftables"
    PACKAGE = "nftables"
    PLANNED = ["zones", "rules", "nat"]

    def run_action(self, action: str, params: dict | None = None):
        if action == "ruleset":
            from .. import packages as pkg
            return pkg.nft_ruleset()
        return super().run_action(action, params)

    def actions(self) -> list[str]:
        return super().actions() + ["ruleset"]
