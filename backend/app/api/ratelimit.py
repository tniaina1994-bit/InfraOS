"""Rate limiting memoire — anti bruteforce /auth/login (5/min/IP defaut).

Sans dependance externe (stdlib). Limites via env :
INFRAOS_RATE_LOGIN_N (defaut 5), INFRAOS_RATE_LOGIN_WINDOW (defaut 60s).
Depassement -> 429 + evenement audit.
"""
from __future__ import annotations
import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException

_hits: dict[str, deque] = defaultdict(deque)


def check(request: Request, n: int = 5, window: int = 60,
          scope: str = "login") -> None:
    import os
    n = int(os.getenv("INFRAOS_RATE_LOGIN_N", n))
    window = int(os.getenv("INFRAOS_RATE_LOGIN_WINDOW", window))
    ip = request.client.host if request and request.client else "?"
    key = f"{scope}:{ip}"
    now = time.time()
    dq = _hits[key]
    while dq and now - dq[0] > window:
        dq.popleft()
    if len(dq) >= n:
        raise HTTPException(429, "trop de tentatives, reessayez dans une minute")
    dq.append(now)


def reset() -> None:
    _hits.clear()
