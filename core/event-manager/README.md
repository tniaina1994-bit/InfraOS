# event-manager — bus d'événements in-process (pas de broker requis)

Implémentation : `core/infraos/event_manager.py`.

- Types fermés (`user.login`, `module.enabled/disabled/installed`, `service.action`,
  `config.updated`, `updates.available`, `job.done/error`, `health.degraded`)
- Persisté `audit_events` + bus mémoire (200) + pubsub Redis best-effort
- Émis par : login, modules, utilisateurs, services, config
- API : `GET /api/v1/events?limit=` (operator+)
- Tests : `core/tests/test_core_managers.py`, `api/tests/test_core_managers.py`
