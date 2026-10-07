# SPDX-License-Identifier: GPL-3.0-or-later
"""DHCP Manager — pilote Kea Debian (phase ulterieure : scopes, baux)."""
from ..module_base import SimpleServiceModule


class DhcpModule(SimpleServiceModule):
    name = "dhcp"
    SERVICE = "kea-dhcp4-server"
    PACKAGE = "kea-dhcp4-server"
    PLANNED = ["scopes", "leases", "reservations"]
