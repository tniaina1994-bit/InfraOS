# SPDX-License-Identifier: GPL-3.0-or-later
"""Sessions JWT revocables — une ligne par login (jti), revocable (logout).

Politique stricte : un token dont le jti est inconnu ou revoque est refuse.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from .db import get_session
from .models import Session as SessionRow


def register(username: str, jti: str, expire_min: int) -> None:
    s = get_session()
    try:
        s.add(SessionRow(username=username, jti=jti,
                         expires_at=datetime.now(timezone.utc) + timedelta(minutes=expire_min)))
        s.commit()
    finally:
        s.close()


def valid(username: str, jti: str) -> bool:
    if not jti:
        return False
    s = get_session()
    try:
        row = s.query(SessionRow).filter_by(jti=jti, username=username).first()
        if not row or row.revoked:
            return False
        exp = row.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp > datetime.now(timezone.utc)
    finally:
        s.close()


def revoke(username: str, jti: str) -> bool:
    s = get_session()
    try:
        row = s.query(SessionRow).filter_by(jti=jti, username=username).first()
        if not row:
            return False
        row.revoked = True
        s.commit()
        return True
    finally:
        s.close()


def list_for(username: str) -> list[dict]:
    s = get_session()
    try:
        rows = (s.query(SessionRow).filter_by(username=username)
                .order_by(SessionRow.id.desc()).limit(20).all())
        return [{"id": r.id, "created_at": str(r.created_at),
                 "expires_at": str(r.expires_at), "revoked": r.revoked}
                for r in rows]
    finally:
        s.close()
