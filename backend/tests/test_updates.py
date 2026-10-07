"""Tests: updates reste sur APT natif, lecture seule, sans exception."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from infraos import updates


def test_check_updates_shape():
    d = updates.check_updates()
    assert "pending" in d and "backend" in d
    assert isinstance(d["pending"], int)


def test_list_sources_shape():
    out = updates.list_sources()
    assert isinstance(out, list)
    for s in out:
        assert {"name", "uri", "suite", "signed", "managed"} <= set(s)


def test_add_source_validation():
    # nom : traversal, caracteres dangereux, vide
    for bad in ("../evil", "UPPER", "a b", "", "x" * 80, "n;rm"):
        with pytest.raises(ValueError):
            updates.add_source(bad, "https://deb.example.org")
    # URL : scheme non http(s), injection d'espace/quotes
    for bad_url in ("ftp://x.example.org", "https://a b.example.org",
                    "https://x.example.org\ndeb evil", "javascript:x", ""):
        with pytest.raises(ValueError):
            updates.add_source("valid-name", bad_url)
    # suite / composants invalides
    with pytest.raises(ValueError):
        updates.add_source("valid-name", "https://deb.example.org",
                           suite="bookworm;rm -rf /")
    with pytest.raises(ValueError):
        updates.add_source("valid-name", "https://deb.example.org",
                           components="main\nEvil: 1")
    # cle GPG : https exige
    with pytest.raises(ValueError):
        updates.add_source("valid-name", "https://deb.example.org",
                           key_url="http://insecure.example.org/key")


def test_remove_source_guards():
    with pytest.raises(ValueError):
        updates.remove_source("../evil")
    # fichier inexistant -> refus (aucune suppression hors prefixe infraos)
    with pytest.raises(ValueError):
        updates.remove_source("source-qui-nexiste-pas-7z9q")
