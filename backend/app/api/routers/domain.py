"""Domaine — readiness Samba AD (lecture seule, operator+)."""
from fastapi import APIRouter, Depends
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos import domain as dom
from deps import require_role

router = APIRouter()


@router.get("/readiness")
def readiness(user: dict = Depends(require_role("operator"))):
    return dom.readiness()
