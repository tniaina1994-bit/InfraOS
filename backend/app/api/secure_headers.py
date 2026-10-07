"""Headers de securite (defense en profondeur ; TLS termine par nginx)."""
from __future__ import annotations
from starlette.middleware.base import BaseHTTPMiddleware

HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; "
                               "style-src 'self' 'unsafe-inline'; img-src 'self' data:",
}


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        for k, v in HEADERS.items():
            resp.headers[k] = v
        return resp
