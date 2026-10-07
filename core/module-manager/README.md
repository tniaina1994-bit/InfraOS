# module-manager — gestionnaire des modules du monolithe

Implémentation : `core/infraos/module_manager.py` (+ `module_state.py`, `module_base.py`,
backends `core/infraos/modules/{system,identity,dns,network}.py`).

- Découverte `modules/*/manifest.yaml`, tri topo `requires`
- Lifecycle : status / enable / disable / install / action
- État persistant `/var/lib/infraos/modules.json`
- API : `GET /api/v1/modules`, `GET /modules/{n}`, `POST /modules/{n}/{enable,disable,install,action}`
- Tests : `core/tests/test_module_manager.py`, `test_module_backends.py`, `api/tests/test_modules.py`
