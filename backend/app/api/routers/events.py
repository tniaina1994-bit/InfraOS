"""Événements — lecture du bus (operator+). Écriture via les actions métier."""
from fastapi import APIRouter, Depends
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos import event_manager as em
from deps import require_role

router = APIRouter()


@router.get("")
def list_events(limit: int = 50, user: dict = Depends(require_role("operator"))):
    return {"events": em.recent(limit), "types": sorted(em.EVENT_TYPES)}
