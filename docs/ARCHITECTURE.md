# Architecture InfraOS — modular monolith (ADR-001)

## Décision : monolithe modulaire, pas de microservices

Un seul processus (`infraos-api` via systemd), une seule DB (PostgreSQL),
un seul frontend servi par nginx. Les modules sont des classes Python
appelées **en-process** par le Module Manager — jamais des services réseau.

```
Admin Web (React+TS) ──REST──▶ InfraOS Core (FastAPI, 1 service systemd)
                                    │             │           │
                              PostgreSQL       Redis    Module Manager
                                                              │
                                   ┌────────────┼────────────┐
                                   ▼            ▼            ▼           ▼
                             System Manager Identity Module DNS Module Network Module
                              (état hôte)   (users/groups)  (BIND9)   (ip/nft)
```

## Pourquoi pas microservices
- Cible : un serveur (bare-metal/VM/LXC), pas un cluster. Le réseau local
  entre services serait du gaspillage et des pannes en plus.
- 1 binaire à packager (.deb), 1 service à superviser, 1 backup DB.
- Transactions simples (pas de saga), debug simple (1 log, 1 stack).

## Quand (peut-être) découper — plus tard, sur preuves
- Un worker de tâches lourdes (backups) si le monolithe sature → file Redis
  déjà prévue (`tasks.py`), worker = même code, 2e service systemd.
- Jamais avant d'avoir des métriques qui l'exigent.

## Contrat d'un module
1. `modules/<nom>/manifest.yaml` (spec point 7) :
   ```yaml
   name: dns
   display_name: DNS Manager   # alias: title
   version: 0.1.0
   description: DNS management module
   enabled: false              # defaut si aucun etat runtime (sinon modules.json)
   dependencies: [core]        # alias: requires
   services: [bind9]
   ```
   Clés des deux orthographes acceptées et normalisées (`title`/`requires` historiques).
2. Backend `backend/app/core/infraos/modules/<nom>.py` : `InfraModule` + `status()`,
   `actions()` fermée, `run_action()` validée. Système via `exec.run()` uniquement.
3. Cycle de vie : `discover → resolve_order → status/enable/disable/install/uninstall`.
   `disable`/`uninstall` refusés si des modules actifs en dépendent.
   `install`/`uninstall` = `apt-get install/remove` des `packages:` du manifest
   (noms validés, RBAC admin, audité).
4. État `enabled` persistant (`/var/lib/infraos/modules.json`, 0600).
5. Routes : `GET /modules`, `GET /modules/{n}`, `GET /modules/{n}/dependencies`,
   `POST /modules/{n}/{enable,disable,install,uninstall,action}`
   (RBAC operator+/admin pour install/uninstall, audit + événement systématiques).

## Règles anti-dispersion
- Interdit : nouveau port, nouveau service systemd, nouvelle DB, appel HTTP
  inter-module. Tout passe par le manager en-process.
- `scripts/test/no-microservice.sh` (CI) : 1 seul `FastAPI()` dans `backend/app/api/`.
