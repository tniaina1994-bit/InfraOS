# config-manager — configuration persistante et validée

Implémentation : `core/infraos/config_manager.py` (+ `config.py`, template `config/default-config.yaml`).

- Lecture fusionnée `/etc/infraos/config.yaml` + env `INFRAOS_*` (secrets caviardés)
- Écriture : clés `EDITABLE` uniquement (`jwt_expire_min` 5..1440), fichier 0600, audit + événement
- API : `GET /api/v1/config` (operator+), `PUT /api/v1/config` (admin)
- Tests : `core/tests/test_core_managers.py`, `api/tests/test_core_managers.py`
