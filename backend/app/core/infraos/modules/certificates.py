# SPDX-License-Identifier: GPL-3.0-or-later
"""Certificate Manager — inventaire TLS local + suivi expiration (phase ulterieure : ACME)."""
from ..module_base import SimpleServiceModule, ModuleStatus


class CertModule(SimpleServiceModule):
    name = "certificates"
    SERVICE = ""
    PACKAGE = "openssl"
    PLANNED = ["issue", "renew"]

    def run_action(self, action: str, params: dict | None = None):
        if action == "inventory":
            from pathlib import Path
            dirs = [Path("/etc/ssl/certs"), Path("/etc/infraos/certs")]
            n = sum(1 for d in dirs if d.exists() for f in d.glob("*.crt"))
            return {"certificates": n, "dirs": [str(d) for d in dirs if d.exists()]}
        return super().run_action(action, params)

    def actions(self) -> list[str]:
        return super().actions() + ["inventory"]
