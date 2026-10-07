# Identité & Domain Controller — Samba AD DC

Module `identity` — provision d'un domaine Active Directory avec **Samba AD DC**
(jamais de réimplémentation), géré via InfraOS : provision guidée, utilisateurs,
groupes, OU, ordinateurs, politiques de mots de passe, santé, audit.

API : `/api/v1/identity/*` · UI : section « Annuaire & partage » (13 pages) ·
Manifeste : `modules/identity/manifest.yaml`

## Principe

- **Aucun second système d'auth/RBAC** : mêmes rôles `readonly < operator <
  admin < superadmin` (`deps.require_role`), permissions dérivées
  (`GET /users/me/permissions`).
- **Aucune commande shell libre** : tout passe par `exec.run()` avec
  allow-list (`samba-tool`, `kinit`, `klist`, `kdestroy`, `timedatectl`,
  `hostnamectl`, `tar`, `systemctl`) — `test_no_shell.py` veille.
- **Pas de secret en base** : mots de passe de création/reset transités par
  `secret_args` (argv masqué dans l'audit) ou `stdin` (kinit) — jamais dans
  PostgreSQL, jamais dans l'URL.
- **Audit + events** : chaque mutation publie un event `identity.*`
  (jeu fermé `event_manager.EVENT_TYPES`) → `AuditEvent` + `audit.log`, lisible
  via `GET /api/v1/identity/audit`.

## Prérequis (LXC / Proxmox)

Trois constats du provisionnement live (§36) — indispensables en LXC :

1. **Conteneur privilégié obligatoire** : en LXC *unprivileged* (user
   namespace), `samba-tool domain provision` panique à l'étape « self join »
   avec `INTERNAL ERROR: Security context active token stack underflow!`
   (`try_chown` → `set_nt_acl` → `acl_xattr` ne peut pas remapper les
   ownerships dans un userns). Conversion : `vzdump` de sécurité →
   `pct stop` → retirer `unprivileged: 1` de `/etc/pve/lxc/<id>.conf` →
   remapper les owners du rootfs (uid/gid ≥ 100000 → −100000) → `pct start`.
2. **CAP_SYS_TIME** : LXC `common.conf` drop `sys_time` par défaut (une
   conteneur ne doit pas changer l'horloge de l'hôte) → `chronyd` échoue
   fatalement (`adjtimex failed : Operation not permitted`). Patch hôte
   (sauvegarder d'abord) : retirer `sys_time` de la ligne `lxc.cap.drop` de
   `/usr/share/lxc/config/common.conf`. Impact : toutes les conteneurs de
   l'hôte peuvent régler l'horloge — acceptable car une conteneur
   privilégiée est déjà équivalente root hôte.
3. **IP statique** : avec `net0: ip=dhcp`, le client DHCP réécrit
   `/etc/resolv.conf` à chaque boot (DNS du routeur + `search localdomain`)
   par-dessus les clés LXC — le DC perd `nameserver 127.0.0.1` /
   `search <domain>`. L'appliance est donc en IP statique.
4. **Forwarder** : passé à la provision via `--dns-forwarder` (lu dans
   resolv.conf live puis backup `.infraos-bak`, `127.0.0.1` exclu). Un LAN
   peut bloquer 8.8.8.8/1.1.1.1 : le resolver LAN est préféré.

## Étapes de création du domaine (§36)

1. `GET /identity/domain/preflight?domain&netbios&hostname&ip` — vérifications
   (hostname, FQDN, IP locale, /etc/hosts, DNS sortante, passerelle, ports,
   horloge, paquets, provision existant) ; ne modifie rien.
2. `POST /identity/domain/setup` — corps : `domain`, `netbios`, `hostname`,
   `ip`, `admin_password` (8+ car.), `admin_user`, `stop_named`, `confirm`.
   - `confirm=false` → retourne le **plan** (`status=planned`) sans rien faire ;
   - `confirm=true` → exécute : `hostnamectl` → bloc `/etc/hosts` marqué →
     `/etc/krb5.conf` → `/etc/infraos/secrets/` (0700) → paquets → arrêt des
     services (`smbd`, `nmbd`, `winbind` et `named` si conflit port 53) →
     `samba-tool domain provision` (mot de passe masqué) → persistance
     `IdentityDomain` → `systemctl enable --now samba-ad-dc` + attente des
     ports 389/88 et de `SYSVOL` → audit.
   - Chaque étape est tracée : `{step, status: ok|error, detail}`.
3. Vérification : `GET /identity/health` → `overall` = PASS/WARNING/ERROR.

## Pages UI (§15)

| Route | Page | Contenu |
|---|---|---|
| `/identity` | Vue d'ensemble | statut, sante resumee, acces rapide |
| `/identity/domain` | Domaine | assistant 8 etapes, info, backup, uninstall |
| `/identity/users` | Utilisateurs AD | liste, fiche, enable/disable/unlock/reset |
| `/identity/groups` | Groupes AD | liste, membres +/-, create/delete |
| `/identity/ous` | OU | liste, create, delete (confirm+force) |
| `/identity/computers` | Ordinateurs | compte machine, enable/disable |
| `/identity/policies` | Politiques mdp | lecture + ecriture via samba-tool |
| `/identity/kerberos` | Kerberos | realm, KDC, keytab, tickets, test kinit |
| `/identity/ldap` | LDAP | ports, base DN, certificats, test recherche |
| `/identity/dns` | DNS domaine | zones, SRV/A, forward/reverse, query |
| `/identity/health` | Health Check | verifs §20, services §19, temps §18 |
| `/identity/join` | Jointure | consignes Windows + Linux (realmd/sssd) |
| `/identity/audit` | Audit | actions `identity.*` (AuditEvent) |

Les comptes locaux InfraOS (JWT/roles) restent sur `/users`.

## RBAC (§26)

Lecture (operator+) : `identity.read`, `domain.read`, `users.read`,
`groups.read`, `computers.read`, `ou.read`, `identity.policy.read`,
`kerberos.read`, `ldap.read`, `dns.read`, `identity.audit.read`.
Écriture (admin) : `identity.manage`, `domain.manage`, `users.create`,
`users.update`, `users.delete`, `users.disable`, `users.reset_password`,
`groups.manage`, `computers.manage`, `ou.manage`, `identity.policy.manage`,
`identity.test`.

## Santé (§20)

`GET /identity/health` retourne par vérification `{check, status, detail}` :
hostname, FQDN, samba, LDAP 389, Kerberos 88, DNS 53, SRV (`_ldap._tcp`,
`_kerberos._tcp/_udp`, `_kpasswd._tcp/_udp`), forward/reverse, SYSVOL,
NETLOGON, keytab, krb5.conf, synchro NTP (< 5 min pour Kerberos), ports AD.
Requêtes DNS via `dig @127.0.0.1` (le DNS AD est non-authentifié par
protocole ; la RPC `samba-tool dns` exige des identifiants AD et échoue
`NT_STATUS_LOGON_FAILURE` sans ticket). Keytab : un Samba AD DC stocke ses
cles dans `secrets.ldb` — absence de `/etc/krb5.keytab` = PASS explicatif.
Services : `GET /identity/domain/services` (§19).
Temps : `GET /identity/domain/time` (§18).

## Politiques de mots de passe (§14)

`GET /identity/policies` (lecture `samba-tool domain passwordsettings show`) ;
`PUT /identity/policies` applique les bornes : complexité yes/no, historique
0-24, longueur 0-128, âge min 0-998, âge max 0-999, verrouillage 0-999
tentatives / durée / reset.

## Jointure

- **Windows** : DNS primaire = IP du DC → rejoindre le realm →
  `ipconfig /all`, `gpupdate /force` (page `/identity/join`).
- **Linux** : `realmd` + `sssd` + `adcli` (`realm discover` / `realm join`).

## Sauvegarde & désinstallation (§29)

- `POST /identity/domain/backup` → `tar` de `/var/lib/samba/private` (+SYSVOL
  metadata) vers `/var/backups/infraos/samba-identity-<stamp>.tar.gz` (0600).
- `DELETE /identity/domain` sans `confirm` → avertissement + liste des
  changements ; avec `confirm=true` → backup puis `ready_for_uninstall`.
- `POST /modules/identity/uninstall` : **409** si domaine provisionné et sans
  `confirm=true` ; le manifeste porte `keep_packages: true` (Samba/Kerberos ne
  sont jamais désinstallés par le module).

## Tests

`backend/tests/test_identity_dc.py` (34 tests) : états gracieux sans domaine,
mutations refusées (400), RBAC (403), validateurs (noms de groupes avec
espaces autorisés, comptes utilisateur stricts), gardes `exec`
(`$` suffixe admis pour `WS01$`, `$()` refusé).
