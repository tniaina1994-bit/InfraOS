# API InfraOS — documentée (OpenAPI)

- Swagger UI : `http://<lxc>/docs` (via nginx `/docs` → API) ou `:8000/docs` en dev
- ReDoc : `/redoc` — schéma brut : `/openapi.json`
- Santé : `GET /api/health` (alias) et `GET /api/v1/health` (canonique)
- Auth : `POST /api/v1/auth/login` (rate-limit 5/min/IP), `POST /auth/logout`,
  `GET /auth/me`, `GET /auth/sessions`, `DELETE /auth/sessions/{id}`,
  `GET /auth/providers`
- Rôles : `GET /api/v1/roles` (matrice), `POST /roles/users/{u}`,
  `DELETE /roles/users/{u}/{rôle}` (superadmin)
- Identity : `GET /users` (rôle effectif + groupes), `POST /users`,
  `POST /users/{u}/{disable,enable}`, `POST /users/me/password`,
  `GET /users/me/permissions`, `GET/POST /groups`, `POST /groups/{n}/members`
- Domaine : `GET /api/v1/domain/readiness` (Samba AD, lecture seule)
- DNS : CRUD `/dns/zones`, `/dns/zones/{z}/records`, `/dns/servers`, `POST /dns/apply`
- DHCP : CRUD `/dhcp/scopes`, réservations, `GET /dhcp/leases`, `POST /dhcp/apply`
- Firewall : CRUD `/firewall/rules`, `GET /preview`, `POST /apply`
- VPN : CRUD `/vpn/servers`, peers, `POST /servers/{id}/apply`
- IPAM : CRUD `/ipam/networks`, hôtes, `GET /networks/{id}` (usage)
- Réseau : `GET /network/{interfaces,routes,dns-resolver}`, `POST /network/{static,vlan}`
- Découverte : `POST /discovery/scans`, `GET /scans`, `/scans/{id}`, `/compare`, `/arp`
- Monitoring : `GET /current`, `POST /collect`, `GET /history`, agents `POST /agents`, `POST /agents/push`
- Fichiers : CRUD `/shares/shares`, `POST /shares/apply`
- Backup : CRUD `/backup/jobs`, `POST /jobs/{id}/{run,restore}`, `GET /jobs/{id}/runs`, `POST /cron/apply`
- v1 : `/api/v1/system/info`, `/api/v1/services`, `/api/v1/modules`,
  `/api/v1/network/interfaces`, `/api/v1/network/firewall-capabilities`,
  `/api/v1/users` (DB, RBAC operator+), `/api/v1/users/system` (comptes OS),
  `/api/v1/updates`, `/api/v1/jobs` (enqueue + statut), `/api/v1/logs/journal`,
  `/api/v1/logs/package`, `/api/v1/logs/firewall`

Générer le schéma (CI) :
```bash
cd backend/app && python -c "from main import app; import json; print(json.dumps(app.openapi()))" > ../../docs/openapi.json
```
Philo : l'UI ne fait QUE du REST sur ces routes — jamais de SSH/shell direct.
