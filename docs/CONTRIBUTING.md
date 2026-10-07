# Contribuer à InfraOS (GPLv3)

1. Specs : Debian 13, Python 3.11+, natif systemd — pas de Docker obligatoire.
2. Un module = `modules/<nom>/manifest.yaml` (avec `packages:` Debian) + code
   qui passe par `backend/app/core/infraos/exec.py` + route API + page UI + test.
3. Interdits : `shell=True`, `os.system`, `eval`, commande construite avec
   entrée utilisateur, secret versionné, paquet propriétaire obligatoire.
4. Checks avant push : `make lint && make test && make security-check`.
5. Licence : toute contribution sous GPLv3.
