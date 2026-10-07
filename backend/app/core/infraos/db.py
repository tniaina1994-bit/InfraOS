# SPDX-License-Identifier: GPL-3.0-or-later
"""Acces DB — SQLAlchemy 2.x, Postgres (prod) ou SQLite (dev).

URL via Settings.db_url. SQLite: init direct (create_all). Postgres: Alembic.
"""
from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base

_engine = None
_SessionFactory = None


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def init_db(db_url: str):
    global _engine, _SessionFactory
    if db_url.startswith("sqlite"):
        # cree le dossier parent (dev Windows sans /var/lib, CI, tests)
        path = db_url.split("sqlite:///", 1)[-1].split("?")[0]
        if path != ":memory:":
            try:
                from pathlib import Path as _P
                _P(path).parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
    _engine = create_engine(db_url, connect_args=_connect_args(db_url), future=True)
    if db_url.startswith("sqlite"):
        # dev LXC: schema direct; prod Postgres: `alembic upgrade head`
        Base.metadata.create_all(_engine)
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_session() -> Session:
    global _SessionFactory
    if _SessionFactory is None:
        from .config import load_settings
        init_db(load_settings().db_url)
    return _SessionFactory()
