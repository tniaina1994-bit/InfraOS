# Philosophie InfraOS — chaque principe = implémentation + preuve

| # | Principe | Implémentation | Preuve |
|---|----------|----------------|--------|
| 1 | Open source | Licence GPLv3 (`LICENSE`), headers SPDX | `head LICENSE`, `grep -r SPDX` |
| 2 | Gratuit | 0 composant payant, 0 clé, 0 télémétrie | `grep -ri "license key\|subscription" core api || echo OK` |
| 3 | Aucun proprio obligatoire | Que du Debian main + code GPL | `cat iso/packages.list`, `cat docs/DEBIAN-COMPONENTS.md` |
| 4 | Max composants Debian existants | BIND9, Kea, nftables, WireGuard, Samba, APT — manifests déclarent `packages:` | `grep -h packages modules/*/manifest.yaml` |
| 5 | Pas de réimplémentation protocole | Pas de DNS/DHCP/SMB maison : on pilote les daemons via config + systemctl | `grep -r "import.*dns\|dhcp.*server" core || echo OK` |
| 6 | Architecture modulaire | `modules/<nom>/manifest.yaml` + découverte auto `/api/v1/modules` | `curl .../api/v1/modules` |
| 7 | Sécurité dès conception | `backend/app/core/infraos/exec.py` allow-list, `audit.py`, JWT/RBAC (phase suivante), `docs/SECURITY.md` | `make security-check` |
| 8 | Configuration persistante | `/etc/infraos/config.yaml` (0600), `/var/lib/infraos/`, template `config/default-config.yaml` | `ls -l /etc/infraos /var/lib/infraos` |
| 9 | Journalisation complète | `logging_conf.py` → console + `/var/log/infraos/infraos.log` (rotation) + journald ; audit append-only | `journalctl -u infraos-api`, `tail /var/log/infraos/audit.log` |
| 10 | Mises à jour | `backend/app/core/infraos/updates.py` sur APT natif + `GET /api/v1/updates` | `curl .../api/v1/updates` |
| 11 | Documentation complète | `docs/` + OpenAPI `/docs` + README/ARCHITECTURE | `ls docs`, `curl .../openapi.json` |
| 12 | ISO ultérieure | `iso/` live-build reproductible, jamais de conversion LXC→ISO | `bash iso/build.sh` (builder dédié) |
| 13 | Compat Debian 13 | Templates `debian-13-*`, `scripts/debian13-check.sh`, paquets trixie | `make debian13-check` |
| 14 | Code propre/maintenable | `ruff` + Makefile `lint`, structure core/api/ui/modules | `make lint` |
| 15 | API documentée | FastAPI OpenAPI `/docs` `/redoc` `/openapi.json` + `docs/API.md` | `curl .../openapi.json \| head` |
| 16 | Tests automatisés | `pytest backend/tests` + CI GitHub | `make test` |
| 17 | Pas de shell arbitraire Web | `exec.run()` allow-list, `shell=False` partout, `scripts/test/no-arbitrary-shell.sh` en CI | `make security-check` |
