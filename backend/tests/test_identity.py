"""Tests: identity avancee — groupes, permissions, politique mdp, sessions."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import db as dbmod
from infraos.models import User, Group, UserGroup
from infraos.security import hash_password
from infraos import permissions as perm
from infraos import password_policy as policy
from infraos import sessions as sess_mod


def _fresh():
    dbmod._engine = None
    dbmod._SessionFactory = None
    dbmod.init_db("sqlite:///:memory:")
    return dbmod.get_session()


def test_effective_role_from_group():
    s = _fresh()
    s.add(User(username="u1", password_hash=hash_password("pw1234567890"), role="viewer"))
    s.add(Group(name="ops", role="operator"))
    s.commit()
    u = s.query(User).filter_by(username="u1").first()
    g = s.query(Group).filter_by(name="ops").first()
    s.add(UserGroup(user_id=u.id, group_id=g.id))
    s.commit()
    eff = perm.effective_role(u.role, [x.role for x in perm.user_groups(s, u.id)])
    assert eff == "operator"
    assert "users:read" in perm.permissions_for(eff)
    assert "users:write" not in perm.permissions_for(eff)
    s.close()


def test_permissions_matrix():
    assert "services:control" in perm.permissions_for("admin")
    assert "services:control" not in perm.permissions_for("operator")
    assert perm.permissions_for("viewer") == sorted(perm.permissions_for("viewer"))


def test_password_policy():
    policy.check_password("long-mot-de-passe-42")
    for bad in ["court1", "sans-chiffre-du-tout-ici", "aaa1"]:
        try:
            policy.check_password(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} aurait du etre refuse")


def test_sessions_register_valid_revoke():
    dbmod._engine = None
    dbmod._SessionFactory = None
    dbmod.init_db("sqlite:///:memory:")
    sess_mod.register("bob", "jti-1", 60)
    assert sess_mod.valid("bob", "jti-1") is True
    assert sess_mod.valid("bob", "nope") is False
    assert sess_mod.revoke("bob", "jti-1") is True
    assert sess_mod.valid("bob", "jti-1") is False
    assert sess_mod.list_for("bob")[0]["revoked"] is True
