"""Tests: cache fallback memoire + jobs DB (sans Redis obligatoire)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import cache as cache_mod
from infraos import db as dbmod


def test_cache_fallback():
    where = cache_mod.cache_set("tkey", "tval", ttl=60)
    assert where in ("redis", "memory")
    assert cache_mod.cache_get("tkey") == "tval"


def test_enqueue_and_run():
    dbmod._engine = None
    dbmod._SessionFactory = None
    dbmod.init_db("sqlite:///:memory:")
    from infraos import tasks
    jid = tasks.enqueue("updates.check", {})
    out = tasks.run_sync(jid)
    assert out["status"] in ("done", "error")
    st = tasks.get_job(jid)
    assert st["id"] == jid
