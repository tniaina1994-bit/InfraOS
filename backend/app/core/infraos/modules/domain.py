# SPDX-License-Identifier: GPL-3.0-or-later
"""Domain Manager — Samba AD-DC (phase ulterieure : provision, jointure)."""
from ..module_base import SimpleServiceModule


class DomainModule(SimpleServiceModule):
    name = "domain"
    SERVICE = "samba-ad-dc"
    PACKAGE = "samba"
    PLANNED = ["provision", "join", "users"]
