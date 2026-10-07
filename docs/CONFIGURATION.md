# Configuration InfraOS — classification et stockage

| Classe | Où | Exemples | Jamais |
|--------|----|----------|--------|
| Système (fichiers) | `/etc/infraos/infraos.yaml` (+ `config.yaml` legacy), `modules/<m>.yaml`, `security/`, `network/`, `dns.yaml` | jwt_expire_min, forwarders, règles par module | secrets |
| Applicative (DB) | Postgres : zones DNS, scopes DHCP, règles FW, jobs, users/groups | running state métier | mots de passe en clair |
| Secrets (fichiers 0600/0700) | `/etc/infraos/secrets/*`, `backup-pw/`, clés WG | jwt_secret (env), mdp DB (config 0600), clés privées | DB, logs, git |
| Données | Postgres `/var/lib/postgresql`, `/var/lib/infraos/*.db`, `/var/lib/kea`, `/srv/*` | tables, baux, partages | — |
| Runtime (reconstruit) | `/var/lib/infraos/modules.json`, `/run`, logs | enabled, pid, cache | backup critique seul |

- `GET /config` caviarde secrets + URLs (`:***@`) ; `PUT /config` : clés
  `EDITABLE` validées ; `POST /config/secrets/{nom}` (admin, 0600).
- `GET /config/structure` crée et décrit l'arborescence.
