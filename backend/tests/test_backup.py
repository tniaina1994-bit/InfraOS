"""Tests: backup (validation jobs, restore restreint, cron)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos import backup as bk


def test_validate_guards():
    bk.validate_job("restic", "/var/backups/r", ["/etc/hostname"])
    for bad in [("tar", "/x", ["/y"]), ("restic", "", ["/y"]),
                ("restic", "/x", []), ("restic", "/x", ["../evil"]),
                ("rsync", "rel/repo", ["/y"])]:
        try:
            bk.validate_job(*bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} aurait du etre refuse")


def test_restore_restricted():
    for bad in ["/", "/etc/passwd", "/boot/x"]:
        try:
            bk.restore(9999, "latest", bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} aurait du etre refuse")


def test_render_cron_skips_bad():
    from infraos import db as dbmod
    from infraos.models import BackupJob
    dbmod._engine = None
    dbmod._SessionFactory = None
    dbmod.init_db("sqlite:///:memory:")
    s = dbmod.get_session()
    s.add(BackupJob(name="j1", backend="restic", repo="/r", sources='["/x"]',
                    schedule="0 2 * * *"))
    s.commit()
    s.close()
    cron = bk.render_cron()
    assert "infraos-backup-run" in cron and "0 2 * * *" in cron
