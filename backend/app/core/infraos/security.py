# SPDX-License-Identifier: GPL-3.0-or-later
"""Securite auth — stdlib uniquement (hashlib PBKDF2, secrets) + python-jose JWT.

Philo: pas de bcrypt/pile exotique cassee ; JWT HS256 local d'abord.
"""
from __future__ import annotations
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

ALGORITHM = "HS256"
ITERATIONS = 210_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS)
    return f"pbkdf2-sha256${ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, hexdk = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 bytes.fromhex(salt), int(iters))
        return hmac.compare_digest(dk.hex(), hexdk)
    except Exception:
        return False


def create_token(username: str, role: str, secret: str,
                 expire_min: int = 60) -> str:
    import uuid
    now = datetime.now(timezone.utc)
    payload = {"sub": username, "role": role, "jti": uuid.uuid4().hex,
               "iat": int(now.timestamp()),
               "exp": int((now + timedelta(minutes=expire_min)).timestamp())}
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_token(token: str, secret: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except JWTError as e:
        raise ValueError(f"token invalide: {e}")
