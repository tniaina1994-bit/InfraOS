"""Security Center — logs centralises, echecs login, suspect, integrations."""
from fastapi import APIRouter, Depends
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos import security_center as sc
from deps import require_role

router = APIRouter()


@router.get("/overview")
def overview(user: dict = Depends(require_role("operator"))):
    return sc.overview()


@router.get("/failed-logins")
def failed_logins(hours: int = 24, limit: int = 50,
                  user: dict = Depends(require_role("operator"))):
    return {"failed": sc.failed_logins(hours, limit)}


@router.get("/suspicious")
def suspicious(hours: int = 24, user: dict = Depends(require_role("operator"))):
    return {"suspicious": sc.suspicious(hours)}


@router.get("/logs/system")
def logs_system(lines: int = 100, user: dict = Depends(require_role("operator"))):
    return sc.system_logs(lines)


@router.get("/logs/firewall")
def logs_firewall(lines: int = 100, user: dict = Depends(require_role("operator"))):
    return sc.firewall_logs(lines)


@router.get("/integrations")
def integrations(user: dict = Depends(require_role("operator"))):
    return {"integrations": sc.integrations()}
