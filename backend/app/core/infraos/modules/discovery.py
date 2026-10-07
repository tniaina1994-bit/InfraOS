# SPDX-License-Identifier: GPL-3.0-or-later
"""Network Discovery — nmap (phase ulterieure : scans, inventaire)."""
from ..module_base import SimpleServiceModule


class DiscoveryModule(SimpleServiceModule):
    name = "discovery"
    SERVICE = ""
    PACKAGE = "nmap"
    PLANNED = ["scan", "hosts"]
