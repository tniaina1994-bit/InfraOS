"""Tests: DB SQLite memoire + auth locale + stubs AD/LDAP/Kerberos."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import db as dbmod
from infraos.models import User
from infraos.security import hash_password
from infraos import auth_providers
from types import SimpleNamespace


def _fresh():
    dbmod._engine = None
    dbmod._SessionFactory = None
    dbmod.init_db("sqlite:///:memory:")
    s = dbmod.get_session()
    s.add(User(username="tadmin", password_hash=hash_password("pw123"),
               role="admin", auth_source="local"))
    s.commit()
    return s


def test_authenticate_local_ok():
    s = _fresh()
    r = auth_providers.authenticate_local("tadmin", "pw123", s)
    assert r.role == "admin"
    s.close()


def test_authenticate_local_ko():
    s = _fresh()
    try:
        auth_providers.authenticate_local("tadmin", "bad", s)
    except ValueError:
        s.close()
        return
    s.close()
    raise AssertionError("mauvais mdp aurait du echouer")


def test_stubs_not_configured():
    s = SimpleNamespace(ldap_url="", ldap_base_dn="", ad_domain="", kerberos_realm="")
    for fn in (auth_providers.authenticate_ldap, auth_providers.authenticate_ad,
               auth_providers.authenticate_kerberos):
        try:
            fn("u", "p", s)
        except auth_providers.NotConfigured:
            continue
        raise AssertionError(f"{fn.__name__} aurait du lever NotConfigured")
