"""Services — lecture (publique/dev) et mutations admin auditées."""
from fastapi import APIRouter, Depends, HTTPException
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.system import services_status
from infraos import service_manager as sm
from infraos import event_manager as em
from deps import require_role

router = APIRouter()

@router.get("")
def list_services():
    return {"services": services_status()}


@router.post("/{name}/{action}")
def service_action(name: str, action: str,
                   user: dict = Depends(require_role("admin"))):
    try:
        out = sm.control(name, action, actor=user["username"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        em.publish("service.action", user["username"], f"{action} {name} rc={out['rc']}")
    except Exception:
        pass
    return out
