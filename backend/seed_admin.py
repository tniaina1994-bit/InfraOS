#!/usr/bin/env python3
"""Seed admin local — idempotent. Mdp via INFRAOS_ADMIN_PASSWORD (defaut: change-me)."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app", "core"))
from infraos.config import load_settings
from infraos.db import init_db, get_session
from infraos.models import User
from infraos.security import hash_password

s = load_settings()
init_db(os.getenv("INFRAOS_DB_URL", s.db_url))
db = get_session()
pwd = os.getenv("INFRAOS_ADMIN_PASSWORD", s.admin_password)
u = db.query(User).filter_by(username=s.admin_user).first()
if u:
    print(f"admin {s.admin_user} existe deja (id={u.id})")
else:
    db.add(User(username=s.admin_user, password_hash=hash_password(pwd),
                role="admin", display_name="Administrateur", auth_source="local"))
    db.commit()
    print(f"admin {s.admin_user} cree")
db.close()
