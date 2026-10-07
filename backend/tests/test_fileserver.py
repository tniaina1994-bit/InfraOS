"""Tests: fileserver (validation partages, rendu smb.conf)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import fileserver as smb


def test_validate_guards():
    smb.validate_share("docs", "/srv/docs", "alice", "admins")
    for bad in [("global", "/srv/x"), ("homes", "/srv/x"), ("bad name!", "/srv/x"),
                ("docs", "rel/path"), ("docs", "/srv/x", "a;b")]:
        try:
            smb.validate_share(*bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} aurait du etre refuse")


def test_render():
    shares = [{"name": "docs", "path": "/srv/docs", "comment": "Docs",
               "read_only": False, "browsable": True, "guest_ok": False,
               "valid_users": "alice", "valid_groups": "admins", "enabled": True},
              {"name": "old", "path": "/srv/old", "enabled": False}]
    txt = smb.render_shares(shares)
    assert "[docs]" in txt and "path = /srv/docs" in txt
    assert "valid users = alice, @admins" in txt
    assert "[old]" not in txt
