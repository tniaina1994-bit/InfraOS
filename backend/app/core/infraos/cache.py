# SPDX-License-Identifier: GPL-3.0-or-later
"""Cache — Redis quand dispo (Debian redis-server), memoire sinon.

Philo: Redis pour jobs/cache/file d'evenements plus tard ; le code tourne
sans Redis (LXC dev minimal) grace au fallback.
"""
from __future__ import annotations
import json
import time

_mem: dict[str, tuple[str, float]] = {}


def _redis():
    try:
        import redis
        from .config import load_settings
        url = load_settings().redis_url
        r = redis.Redis.from_url(url, socket_connect_timeout=2)
        r.ping()
        return r
    except Exception:
        return None


def cache_get(key: str) -> str | None:
    r = _redis()
    if r is not None:
        try:
            v = r.get(f"infraos:{key}")
            return v.decode() if v else None
        except Exception:
            pass
    v = _mem.get(key)
    if not v:
        return None
    val, exp = v
    if exp and time.time() > exp:
        _mem.pop(key, None)
        return None
    return val


def cache_set(key: str, value: str, ttl: int = 300) -> str:
    r = _redis()
    if r is not None:
        try:
            r.setex(f"infraos:{key}", ttl, value)
            return "redis"
        except Exception:
            pass
    _mem[key] = (value, time.time() + ttl if ttl else 0)
    return "memory"


def backend() -> str:
    return "redis" if _redis() is not None else "memory"
