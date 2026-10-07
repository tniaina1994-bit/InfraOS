# SPDX-License-Identifier: GPL-3.0-or-later
"""Security Center — fail2ban + audit (phase ulterieure : jails, durcissement)."""
from ..module_base import SimpleServiceModule


class SecurityModule(SimpleServiceModule):
    name = "security"
    SERVICE = "fail2ban"
    PACKAGE = "fail2ban"
    PLANNED = ["jails", "bans"]
