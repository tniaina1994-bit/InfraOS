# SPDX-License-Identifier: GPL-3.0-or-later
"""Log Analyzer — stats journald (lecture seule ; phase ulterieure : recherches)."""
from ..module_base import SimpleServiceModule, ModuleStatus


class LogAnalyzerModule(SimpleServiceModule):
    name = "loganalyzer"
    SERVICE = "systemd-journald"
    PACKAGE = ""
    PLANNED = ["search"]

    def run_action(self, action: str, params: dict | None = None):
        if action == "tail":
            from ..journal import read_logs
            p = params or {}
            return read_logs(str(p.get("service", "infraos-api")), int(p.get("lines", 50)))
        return super().run_action(action, params)

    def actions(self) -> list[str]:
        return super().actions() + ["tail"]
