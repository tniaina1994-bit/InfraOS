# Updates — apt/dpkg comme base (jamais remplacés)

- `GET /updates` (check : nb), `/updates/list` (détail), `/updates/security`
  (sous-ensemble dépôts security via `apt-cache policy`), `/updates/package?name=`
- `POST /updates/install {"packages": [...]}` (admin) : noms Debian validés,
  liste **explicite** exigée (pas de full-upgrade aveugle), audité + historisé
  (`update_runs`, `GET /updates/history`)
- Base : `apt-get update`, `apt list --upgradable`, `apt-get install -y`,
  `dpkg -l/-s`. Auto sécurité : `unattended-upgrades` (ISO + LXC).
