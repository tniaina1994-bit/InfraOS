"""Logs natifs — journald + audit (lecture seule)."""
from fastapi import APIRouter, Depends
import sys
from pathlib import Path
for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.journal import read_logs
from infraos.packages import is_installed, nft_ruleset
from deps import require_role

router = APIRouter()


@router.get("/journal")
def journal(service: str = "infraos-api", lines: int = 50,
            user: dict = Depends(require_role("operator"))):
    return read_logs(service, lines)


@router.get("/package")
def package(name: str, user: dict = Depends(require_role("operator"))):
    return is_installed(name)


@router.get("/firewall")
def firewall_rules(user: dict = Depends(require_role("operator"))):
    return nft_ruleset()
