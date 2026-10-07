"""Tests: hash PBKDF2 + JWT local."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import security


def test_hash_verify():
    h = security.hash_password("secret123")
    assert security.verify_password("secret123", h)
    assert not security.verify_password("nope", h)


def test_jwt_roundtrip():
    t = security.create_token("admin", "admin", "test-secret", 60)
    d = security.decode_token(t, "test-secret")
    assert d["sub"] == "admin" and d["role"] == "admin"


def test_jwt_bad_secret():
    t = security.create_token("admin", "admin", "s1", 60)
    try:
        security.decode_token(t, "s2")
    except ValueError:
        return
    raise AssertionError("mauvais secret aurait du echouer")
