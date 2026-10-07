# SPDX-License-Identifier: GPL-3.0-or-later
"""IPAM — inventaire sous-reseaux (phase ulterieure : allocations, conflits)."""
from ..module_base import SimpleServiceModule


class IpamModule(SimpleServiceModule):
    name = "ipam"
    SERVICE = ""
    PACKAGE = ""
    PLANNED = ["subnets", "allocations"]
