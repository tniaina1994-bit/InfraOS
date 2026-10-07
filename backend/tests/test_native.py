"""Tests: natifs Linux couverts (journald/dpkg/nft/ip) sans jamais lever Forbidden."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos.exec import run, ForbiddenCommand
from infraos import journal, packages


def test_nft_allowlisted():
    try:
        r = run("nft", "list", "ruleset", caller="test")
    except ForbiddenCommand:
        raise AssertionError("nft list devrait etre allow-liste")
    assert isinstance(r.rc, int)


def test_journal_graceful():
    d = journal.read_logs("infraos-api", 5)
    assert "logs" in d


def test_dpkg_graceful():
    d = packages.is_installed("bind9")
    assert "installed" in d


def test_bad_service_rejected():
    try:
        journal.read_logs("a;b", 5)
    except ValueError:
        return
    raise AssertionError("service dangereux aurait du etre refuse")
