# Backup — restic/borgbackup/rsync (open source uniquement)

- Jobs (backend, repo, sources absolues, schedule cron, rétention, chiffrement) ;
  mots de passe en `/etc/infraos/backup-pw/<id>.pw` (0600, générés).
- Exécution admin (`POST /jobs/{id}/run`, timeout 30 min), logs
  `/var/log/infraos/backups/<run>.log` + miroir DB, rétention
  (`forget --prune` / `prune`), statut + historique (`/jobs/{id}/runs`).
- Restore admin, cible **restreinte** (`/var/lib/infraos/restore/`, `/tmp/`).
- Schedules : `POST /cron/apply` → `/etc/cron.d/infraos-backup`
  (`infraos-backup-run <id>` — script CLI à créer avec le worker).
- PBS : prévu — client `proxmox-backup-client` + datastore, même modèle
  job/run (backend `pbs`, phase ultérieure).
