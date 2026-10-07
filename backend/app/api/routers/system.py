from fastapi import APIRouter, Depends, HTTPException
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.system import services_status, os_info
from infraos import service_manager as sm
from infraos import health_manager as hm
from deps import require_role

router = APIRouter()

@router.get("/info")
def info():
    return os_info()


@router.get("/health")
def health_detail(user: dict = Depends(require_role("operator"))):
    return hm.check()
