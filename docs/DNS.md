# DNS InfraOS — BIND9 natif, DLZ Samba prévu

## Backend actif : fichiers BIND9 (v1)
- Source de vérité : tables `dns_zones` / `dns_records` (Postgres/SQLite)
- Rendu : `/etc/bind/infraos/db.<zone>` + `named.conf.infraos`
  (zones master + forward, options forwarders), inclus depuis `named.conf`
- Sécurité : `named-checkconf` **obligatoire** avant `rndc reload`
  (allow-list `exec.py`, RBAC admin, audit + événement)
- Types : A, AAAA, CNAME (exclusif RFC 1034), MX, TXT, PTR, NS ;
  zones forward + reverse (`in-addr.arpa`/`ip6.arpa`), TTL par zone/record,
  sérial auto date-based.

## Backend prévu : Samba DLZ
Si `/var/lib/samba/private/sam.ldb` existe (AD provisionné via
`scripts/install/provision-ad.sh`), `GET /dns/servers` → `backend.samba_dlz =
available-manual`. La zone DLZ (`samba_dlz`, `dlz "AD DNS"`) se déclare
alors dans `named.conf` au lieu des fichiers plats — procédure :
1. arrêter l'apply fichiers pour la zone AD, 2. déclarer le DLZ,
3. `named-checkconf` + reload. Non exécuté automatiquement en v1
   (documenté, action `dlz` → `planned`).

## API
`GET/POST /dns/zones`, `DELETE /dns/zones/{z}`,
`GET/POST /dns/zones/{z}/records`, `DELETE /dns/records/{id}`,
`GET/PUT /dns/servers` (forwarders), `POST /dns/apply`.
