# health-manager — santé agrégée du système

Implémentation : `core/infraos/health_manager.py`.

- Checks : db (SELECT 1), cache (backend), disque <90%, mémoire <95%, services critiques (ssh, infraos-api)
- Statuts : ok | degraded | down ; événement `health.degraded` si non-ok
- API : `GET /api/health` (rapide, public), `GET /api/v1/system/health` (détail, operator+)
- Tests : `core/tests/test_core_managers.py`
