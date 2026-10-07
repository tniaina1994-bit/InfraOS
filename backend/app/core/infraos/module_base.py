"""Base class every InfraOS module must extend.

Philo: les modules reutilisent les paquets Debian (bind9, kea, nftables...)
declarés dans leur manifest — jamais de reimplementation de protocole.
Actions systeme uniquement via exec.run() (allow-list + audit).
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml
from .exec import run, ForbiddenCommand


@dataclass
class ModuleStatus:
    name: str
    installed: bool
    enabled: bool
    running: bool
    detail: str = ""


class InfraModule:
    name: str = "base"
    manifest_path: str = ""

    @classmethod
    def from_manifest(cls, path: str | Path) -> dict:
        return yaml.safe_load(Path(path).read_text())

    def status(self) -> ModuleStatus:
        raise NotImplementedError

    def install(self) -> str:
        raise NotImplementedError

    def actions(self) -> list[str]:
        """Noms d'actions exposees (validees une par une dans run_action)."""
        return []

    def run_action(self, action: str, params: dict | None = None) -> dict:
        raise ValueError(f"action inconnue: {action}")

    def _service_state(self, service: str) -> str:
        """Lecture d'etat allow-listee (is-active). Le nom doit venir du manifest."""
        r = run("systemctl", "is-active", service, caller=f"module.{self.name}")
        return r.out.strip() or "unknown"

    # NOTE: pas de _systemctl(*args) generique volontairement :
    # un passage d'arguments libres depuis le Web est interdit (philo securite).


class SimpleServiceModule(InfraModule):
    """Backend standard des modules futurs (point 8) : etat reel
    (paquet Debian installe ? service actif ?) + actions planifiees
    declarees mais non implementees (phase ulterieure, sans echec).

    SERVICE/PACKAGE : noms Debian (ex. SERVICE="named", PACKAGE="bind9").
    PLANNED : actions declarees pour la roadmap (run -> status planned).
    """
    SERVICE: str = ""
    PACKAGE: str = ""
    PLANNED: list[str] = []

    def status(self) -> ModuleStatus:
        from . import packages as pkg
        inst = pkg.is_installed(self.PACKAGE).get("installed", False) if self.PACKAGE else True
        state = self._service_state(self.SERVICE) if self.SERVICE else "n/a"
        running = (state == "active") if self.SERVICE else False
        return ModuleStatus(name=self.name, installed=bool(inst), enabled=True,
                            running=running,
                            detail=f"{self.PACKAGE or 'natif'} installe={inst}, "
                                   f"{self.SERVICE or 'pas de service'}={state}")

    def actions(self) -> list[str]:
        return ["status"] + list(self.PLANNED)

    def run_action(self, action: str, params: dict | None = None) -> dict:
        if action == "status":
            st = self.status()
            return {"installed": st.installed, "running": st.running, "detail": st.detail}
        if action in self.PLANNED:
            return {"status": "planned",
                    "detail": f"action {action} prevue (module {self.name}, phase ulterieure)"}
        raise ValueError(f"action inconnue: {action}")
