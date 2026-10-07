"""Tests: matrice 4 roles + seed RBAC idempotent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import db as dbmod
from infraos import permissions as perm


def test_four_roles():
    assert perm.RANK["superadmin"] > perm.RANK["admin"] > perm.RANK["operator"]
    assert perm.RANK["readonly"] == perm.RANK["viewer"] == 0
    assert perm.canon("viewer") == "readonly"
    assert "roles:manage" in perm.permissions_for("superadmin")
    assert "roles:manage" not in perm.permissions_for("admin")
    assert set(perm.permissions_for("readonly")) <= set(perm.permissions_for("operator"))
    assert set(perm.permissions_for("operator")) <= set(perm.permissions_for("admin"))
    assert set(perm.permissions_for("admin")) <= set(perm.permissions_for("superadmin"))


def test_seed_rbac():
    dbmod._engine = None
    dbmod._SessionFactory = None
    dbmod.init_db("sqlite:///:memory:")
    s = dbmod.get_session()
    out1 = perm.seed_rbac(s)
    out2 = perm.seed_rbac(s)
    assert out1["roles"] == 4 and out2["roles"] == 4
    assert out1["permissions"] == out2["permissions"] > 10
    s.close()
