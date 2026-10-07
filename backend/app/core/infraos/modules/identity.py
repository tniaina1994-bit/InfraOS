# SPDX-License-Identifier: GPL-3.0-or-later
"""Identity Module — comptes DB InfraOS (auth locale) + Domaine Samba AD DC."""
from __future__ import annotations
from ..module_base import InfraModule, ModuleStatus
from ..db import get_session
from ..models import User, Group


class IdentityModule(InfraModule):
    name = "identity"

    def status(self) -> ModuleStatus:
        try:
            s = get_session()
            try:
                n_users = s.query(User).count()
                n_groups = s.query(Group).count()
            finally:
                s.close()
            ad = ""
            try:
                from ..identity_domain import is_provisioned, domain_row
                if is_provisioned():
                    row = domain_row()
                    ad = f" | AD: {row.realm if row else '?'}"
            except Exception:
                pass
            return ModuleStatus(name=self.name, installed=True, enabled=True,
                                running=True,
                                detail=f"{n_users} utilisateurs, "
                                       f"{n_groups} groupes (DB){ad}")
        except Exception as e:
            return ModuleStatus(name=self.name, installed=True, enabled=True,
                                running=False, detail=f"DB indisponible: {e}")

    def actions(self) -> list[str]:
        return ["count", "system_accounts"]

    def run_action(self, action: str, params: dict | None = None) -> dict:
        if action == "count":
            st = self.status()
            return {"detail": st.detail}
        if action == "system_accounts":
            try:
                import pwd
                out = [{"name": p.pw_name, "uid": p.pw_uid}
                       for p in pwd.getpwall() if p.pw_uid >= 1000 or p.pw_name == "root"]
                return {"accounts": out, "count": len(out)}
            except ImportError:
                return {"accounts": [], "count": 0, "detail": "pwd indisponible"}
        raise ValueError(f"action inconnue: {action}")
