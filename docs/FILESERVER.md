# File Server Samba — partages, permissions, AD prévu

- CRUD `samba_shares` (nom réservés refusés, chemin absolu sans `..`,
  valid users/groups) → `/etc/samba/smb-infraos.conf` inclus depuis
  `smb.conf` (backup auto) → `testparm -s` obligatoire → `restart smbd/nmbd`.
- Permissions : valid users/groups (comptes InfraOS/AD), read only, guest.
  ACL POSIX (`setfacl`) et quotas (`setquota`) : champs prévus, enforcement
  phase 2. Stockage : usage disque des chemins (phase 2).
- AD : `security = ADS` + `realm join` prévus au provisionnement du domaine
  (`docs/DOMAIN.md`) ; workgroup/realm paramétrables alors.
