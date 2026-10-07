# Audit & logs InfraOS — journald + audit tuple

## Tuple d'audit (spec)
`User | Action | Resource | Timestamp | IP | Result`
ex. `admin | ENABLE_MODULE | dns | 2026-09-30 10:30 | 192.168.20.10 | SUCCESS`

## Implémentation
- Fichier append-only `/var/log/infraos/audit.log` (0600) :
  `<ts> user=<u> action=<a> resource=<r> ip=<ip> result=<SUCCESS|FAILURE|DENIED> ...`
- Miroir DB `audit_events` (actor/action/resource/ip/result/ts) → `GET /events`
- Middleware : chaque requête HTTP auditée (IP client, méthode+chemin, statut→result)
- Échecs login : `user.login` FAILURE + IP → Security Center (bruteforce ≥5/15min)

## Sources
- journald : système (`/security/logs/system`), services (`/logs/journal`),
  firewall/noyau (`/security/logs/firewall`), auth (audit ci-dessus)
- rsyslog / Suricast (eve.json) / Fail2ban : intégrations `planned`
  (`GET /security/integrations`), jamais obligatoires
