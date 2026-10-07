# log-manager — journalisation complète

Implémentation : `core/infraos/log_manager.py` (façade `journal.py` + `logging_conf.py` + `audit.py`).

- journald (`journalctl --no-pager -u <service>`, allow-list), rotation `/var/log/infraos/infraos.log`
- audit append-only `/var/log/infraos/audit.log` (0600) + miroir DB `audit_events`
- API : `GET /api/v1/logs/journal?service=&lines=`, `/logs/package?name=`, `/logs/firewall`
- Tests : `core/tests/test_native.py`
