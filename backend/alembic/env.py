"""Alembic env — URL via INFRAOS_DB_URL (Postgres prod) ou sqlite dev."""
from __future__ import annotations
import os
import sys
from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                "app", "core"))
from infraos.models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
url = os.getenv("INFRAOS_DB_URL", "sqlite:////var/lib/infraos/infraos.db")
engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})


def run_migrations_offline():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
