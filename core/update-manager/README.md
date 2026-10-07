# update-manager — mises à jour APT (natif Debian, lecture seule v1)

Implémentation : `core/infraos/update_manager.py` (façade de `updates.py`).

- `check()` : `apt-get update -qq` + `apt list --upgradable` (rien de réimplémenté)
- Installation ciblée : `core/infraos/apt.py` (manifests, admin, audité)
- API : `GET /api/v1/updates`, jobs `updates.check`
- Tests : `core/tests/test_updates.py`
