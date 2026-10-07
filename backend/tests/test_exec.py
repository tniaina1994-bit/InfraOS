"""Tests: l'executor allow-list est le verrou anti-shell-arbitraire."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infraos.exec import run, ForbiddenCommand, ALLOWED


def test_allowed_list_nonempty():
    assert "systemctl" in ALLOWED and "is-active" in ALLOWED["systemctl"]


def test_forbidden_binary():
    try:
        run("rm", "-rf", "/", caller="test")
    except ForbiddenCommand:
        return
    raise AssertionError("rm aurait du etre interdit")


def test_forbidden_subcommand():
    # mutations start/stop/restart autorisees au niveau exec (RBAC admin cote
    # service_manager) ; le reste (mask, daemon-reload...) reste interdit.
    try:
        run("systemctl", "mask", "ssh", caller="test")
    except ForbiddenCommand:
        return
    raise AssertionError("systemctl mask aurait du etre interdit")


def test_dangerous_chars_rejected():
    for bad in ["a;b", "a|b", "$(id)", "`id`"]:
        try:
            run("systemctl", "is-active", bad, caller="test")
        except ForbiddenCommand:
            continue
        raise AssertionError(f"{bad!r} aurait du etre refuse")


def test_detect_virt_runs_or_notfound():
    r = run("systemd-detect-virt", caller="test")
    assert r.rc in (0, 1, 127)
