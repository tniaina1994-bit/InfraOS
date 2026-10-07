"""Middleware: journalisation complete + audit de chaque requete API."""
from __future__ import annotations
import sys
import time
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

for _p in (Path(__file__).resolve().parents[2] / "core",
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from infraos.audit import audit
from infraos.logging_conf import get_logger

log = get_logger("infraos.api")


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t0 = time.time()
        resp = await call_next(request)
        dt = int((time.time() - t0) * 1000)
        line = f"{request.method} {request.url.path} -> {resp.status_code} {dt}ms"
        log.info(line)
        try:
            ip = request.client.host if request.client else ""
            result = "SUCCESS" if resp.status_code < 400 else (
                "DENIED" if resp.status_code in (401, 403) else "FAILURE")
            audit("api.request", actor="http", resource=f"{request.method} {request.url.path}",
                  ip=ip, result=result, detail=f"{resp.status_code} {dt}ms")
        except Exception:
            pass
        return resp
