# task-manager — tâches asynchrones (file Redis ou table DB)

Implémentation : `core/infraos/task_manager.py` (façade `tasks.py` + `list_recent`/`cancel`).

- `enqueue(kind, payload)` → id ; `run_sync(id)` ; `cancel(id)` (queued uniquement)
- Kinds connus : `updates.check` (autres : worker futur)
- API : `POST /api/v1/jobs`, `GET /api/v1/jobs` (liste), `GET /jobs/{id}`, `DELETE /jobs/{id}`
- Tests : `core/tests/test_cache_tasks.py`
