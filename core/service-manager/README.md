# service-manager — services systemd (lecture + mutations admin)

Implémentation : `core/infraos/service_manager.py` (+ lecture `core/infraos/system.py`).

- Lecture : `systemctl is-active` sur liste fermée (constantes + services des manifests)
- Mutations : start/stop/restart/enable/disable — nom validé, RBAC **admin**, audit + événement
- API : `GET /api/v1/services`, `POST /api/v1/services/{nom}/{action}` (admin)
- Tests : `core/tests/test_core_managers.py`, `api/tests/test_core_managers.py`
