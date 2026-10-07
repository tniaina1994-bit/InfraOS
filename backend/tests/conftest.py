"""Pytest bootstrap — backend/app (main), backend/app/api (routers),
backend/app/core (infraos)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/tests -> backend
APP = ROOT / "app"
for p in (str(APP), str(APP / "api"), str(APP / "core")):
    if p not in sys.path:
        sys.path.insert(0, p)
