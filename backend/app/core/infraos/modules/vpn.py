# SPDX-License-Identifier: GPL-3.0-or-later
"""VPN Manager — WireGuard (phase ulterieure : peers, tunnels)."""
from ..module_base import SimpleServiceModule, ModuleStatus


class VpnModule(SimpleServiceModule):
    name = "vpn"
    SERVICE = ""
    PACKAGE = "wireguard"
    PLANNED = ["peers", "tunnels"]

    def status(self) -> ModuleStatus:
        base = super().status()
        try:
            import psutil
            wg = [n for n in psutil.net_if_addrs() if n.startswith("wg")]
            base.detail += f" | interfaces wg={wg or 'aucune'}"
            base.running = bool(wg)
        except Exception:
            pass
        return base
