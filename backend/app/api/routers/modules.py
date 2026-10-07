"""Modules — vitrine du Module Manager (monolithe).

Lecture (liste/detail) : operateur+. Mutations (enable/disable) : operateur+,
install : admin. Actions backend validees une par une (jamais de shell libre).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos import module_manager as mm
from infraos import event_manager as em
from deps import require_role, get_current_user

router = APIRouter()


class ActionBody(BaseModel):
    action: str
    params: dict = {}


@router.get("")
def list_modules(user: dict = Depends(require_role("operator"))):
    mods = mm.list_all()
    return {"modules": mods, "count": len(mods),
            "order": _safe_order(mods)}


def _safe_order(mods: list[dict]) -> list[str]:
    try:
        return mm.resolve_order([m for m in mods if "error" not in m])
    except ValueError as e:
        return [f" ordre partiel: {e}"]


@router.get("/{name}")
def module_detail(name: str, user: dict = Depends(require_role("operator"))):
    try:
        return mm.status(name)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{name}/enable")
def module_enable(name: str, user: dict = Depends(require_role("operator"))):
    try:
        out = mm.enable(name, actor=user["username"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        em.publish("module.enabled", user["username"], name)
    except Exception:
        pass
    return out


@router.post("/{name}/disable")
def module_disable(name: str, user: dict = Depends(require_role("operator"))):
    try:
        out = mm.disable(name, actor=user["username"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        em.publish("module.disabled", user["username"], name)
    except Exception:
        pass
    return out


@router.post("/{name}/install")
def module_install(name: str, user: dict = Depends(require_role("admin"))):
    try:
        out = mm.install(name, actor=user["username"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        em.publish("module.installed", user["username"], name)
    except Exception:
        pass
    return out


@router.post("/{name}/uninstall")
def module_uninstall(name: str, confirm: bool = False,
                     user: dict = Depends(require_role("admin"))):
    # §29 : garde Identity — un domaine AD provisionne exige d'abord un backup
    # et la desinstallation explicite du domaine (DELETE /identity/domain).
    if name in ("identity", "users-groups"):
        try:
            from infraos.identity_domain import is_provisioned
            if is_provisioned() and not confirm:
                raise HTTPException(
                    409, "Domaine AD provisionne : lancez d'abord un backup et "
                         "DELETE /api/v1/identity/domain (confirm=true), puis "
                         "reessayez avec ?confirm=true")
        except HTTPException:
            raise
        except Exception:
            pass
    try:
        out = mm.uninstall(name, actor=user["username"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        em.publish("module.uninstalled", user["username"], name)
    except Exception:
        pass
    return out


@router.post("/{name}/action")
def module_action(name: str, body: ActionBody,
                  user: dict = Depends(require_role("operator"))):
    be = mm._backend(name)
    if not be:
        raise HTTPException(404, f"pas de backend manage: {name}")
    if body.action not in be.actions():
        raise HTTPException(400, f"action inconnue: {body.action}")
    try:
        return be.run_action(body.action, body.params)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{name}/dependencies")
def module_dependencies(name: str, user: dict = Depends(require_role("operator"))):
    try:
        return mm.dependencies(name)
    except ValueError as e:
        raise HTTPException(404, str(e))
