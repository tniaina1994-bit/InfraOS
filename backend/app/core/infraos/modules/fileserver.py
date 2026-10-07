# SPDX-License-Identifier: GPL-3.0-or-later
"""File Server — partages Samba (phase ulterieure : shares, quotas, ACL)."""
from ..module_base import SimpleServiceModule


class FileServerModule(SimpleServiceModule):
    name = "fileshare"
    SERVICE = "smbd"
    PACKAGE = "samba"
    PLANNED = ["shares", "quotas"]
