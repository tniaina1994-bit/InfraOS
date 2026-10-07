# Formation — Active Directory avec InfraOS

Formation pratique à l'utilisation et à la configuration d'Active Directory,
fourni par le module **Identité** d'InfraOS (Samba AD DC — open source,
jamais réimplémenté).

| | |
|---|---|
| **Public** | Administrateurs système / réseau (débutants AD acceptés) |
| **Durée** | 1 journée (théorie + lab) |
| **Support** | Lab InfraOS : LXC `infraos-dev` 192.168.10.39, domaine `corp.example.internal` |
| **Prérequis** | Notions Linux (systemd, réseaux), un poste Windows ou Linux d'essai (recommandé) |
| **Identifiants lab** | Voir **`docs/IDENTIFIANTS.md`** (fichier local, jamais committé) |

**Programme** : 1) Concepts · 2) Architecture InfraOS · 3) Provision du domaine ·
4) Gestion quotidienne · 5) DNS AD · 6) Jointure des postes · 7) Santé/audit/backup ·
8) Dépannage · 9) Bonnes pratiques · Évaluation

---

## Module 1 — Concepts Active Directory (théorie, 1h)

### À quoi sert AD
Active Directory est un **annuaire centralisé** qui rend trois services :

1. **Authentification unique** (Kerberos) — un seul compte pour tout le domaine.
2. **Gestion des objets** — utilisateurs, groupes, ordinateurs, OU, politiques.
3. **Application de la stratégie** — GPO (Group Policy Objects) sur les postes Windows.

### Les mots-clés à connaître

| Terme | Définition |
|---|---|
| **Domaine** | Frontière de sécurité et d'administration (ici `corp.example.internal`) |
| **Realm** | Nom Kerberos du domaine, en MAJUSCULES (`CORP.EXAMPLE.INTERNAL`) — un domaine AD = un realm |
| **DC** (Domain Controller) | Serveur qui héberge l'annuaire (`infraos-dev`, 192.168.10.39) |
| **Forest / Forêt** | Ensemble des domaines partageant le même schéma (ici : 1 domaine = 1 forêt) |
| **SID** | Identifiant numérique unique d'un objet AD |
| **sAMAccountName** | Nom de compte court (ex. `lab.user`, `WS01$`) |
| **DN** (Distinguished Name) | Chemin LDAP complet : `CN=Lab Admins,CN=Users,DC=corp,DC=example,DC=internal` |
| **OU** (Organizational Unit) | Dossier dans l'annuaire pour organiser objets et appliquer des GPO |
| **Groupe** | Regroupe des comptes pour attribuer des droits (≠ OU) |

### Les 4 protocoles qui tournent ensemble

| Protocole | Port | Rôle |
|---|---|---|
| **LDAP** | 389 (636 en TLS) | Lecture/écriture de l'annuaire |
| **Kerberos** | 88 | Authentification (tickets, `kinit`) |
| **DNS** | 53 | Localisation des serveurs (SRV `_ldap._tcp`…) |
| **SMB** | 445 | Partages SYSVOL (GPO) et NETLOGON (scripts de logon) |

> **Point clé** : le DC doit être le **DNS de tous les clients** du domaine.
> Sans ça, rien ne fonctionne (pas de logon, pas de jointure).

### Comptes spéciaux
- **Utilisateur** : `lab.user` — mot de passe géré par politiques (§14).
- **Ordinateur** : `WS01$` — le `$` final identifie un compte machine (jointure).
- **Groupes built-in** : `Domain Admins`, `Domain Users`, `Administrators`,
  `Enterprise Admins`… (~40 groupes créés à la provision).
- **Scopes de groupes** (à retenir) : *Global* (droits dans la forêt),
  *Domain Local* (droits localisés), *Universal* (multi-domaines).

### Samba AD DC — pourquoi c'est possible en open source
Samba implémente le protocole AD (LDAP + Kerberos + SMB + DNS). InfraOS ne
réécrit rien : elle **orchestre** `samba-tool` via une API sécurisée.
100 % compatible jointure Windows 10/11, sans licence Microsoft.

**✅ Autoformation** — Répondez sans regarder (corrigé en fin de document) :
1. Quelle est la différence entre une OU et un groupe ?
2. Quel port pour Kerberos ? Et pourquoi le DC doit-il être le DNS des clients ?
3. Quel est le nom Kerberos (realm) du domaine `corp.example.internal` ?

---

## Module 2 — Architecture InfraOS (30 min)

```
 Navigateur (UI /identity/*)
        │  HTTPS/JSON + JWT (rôle admin)
        ▼
 ┌──────────────────────────────────────────────────────┐
 │ infraos-api (FastAPI, monolithe modulaire)           │
 │  routers/identity.py  ── RBAC deps.require_role      │
 │  core/infraos/        ── validateurs (regex)         │
 │         │ exec.run(argv, allow-list)  ← PAS de shell │
 │         ▼                                            │
 │  samba-tool / dig / kinit / systemctl (binaires)     │
 └───────┬──────────────────────────────────────────────┘
         ▼
 samba-ad-dc (LDAP 389 · Kerberos 88 · DNS 53 · SMB 445)
 + chrony (NTP) — DNS local 127.0.0.1 — SYSVOL/NETLOGON
```

**Garanties de sécurité (§ architecture)** :
- **Aucun shell libre** : `exec.run()` avec allow-list et refus des
  métacaractères (`; & | \``…) — test `test_no_shell.py`.
- **Aucun secret en base** : mots de passe transités par argv masqué ou
  `stdin`, jamais dans PostgreSQL ni dans l'URL.
- **Un seul RBAC** : `readonly < operator < admin < superadmin`
  (le module n'invente aucun rôle).
- **Audit complet** : chaque mutation = event `identity.*` + `AuditEvent`.

**Références doc** : `docs/IDENTITY.md` (spécifications),
`docs/ARCHITECTURE.md` (monolithe modulaire), `docs/DOMAIN.md`.

---

## Module 3 — Provision du domaine (lab, 1h)

### 3.1 Prérequis (LXC/Proxmox) — rappels critiques
Le lab actuel a nécessité 3 ajustements (détail : `docs/IDENTITY.md` → Prérequis) :

1. **CT privilégié obligatoire** — en LXC unprivileged, la provision panique
   (`Security context active token stack underflow!`).
2. **CAP_SYS_TIME** — sans elle `chronyd` échoue (`adjtimex`) → patch hôte
   `common.conf` : retirer `sys_time` de `lxc.cap.drop`.
3. **IP statique** — le DHCP réécrit `/etc/resolv.conf` au boot et le DC
   perd son `search corp.example.internal`.

> Sur une installation ISO bare-metal/VM ces contraintes n'existent pas.

### 3.2 Provision guidée (UI)
1. Se connecter : **http://192.168.10.39/** → `admin` (identifiants dans `docs/IDENTIFIANTS.md`).
2. Menu **Annuaire & partage → Domaine** (`/identity/domain`).
3. Saisir : domaine `corp.example.internal`, NetBIOS `CORP`, hôte `infraos-dev`,
   IP `192.168.10.39`, mot de passe `Administrator` (8+ caractères).
4. **Preflight** (`GET /identity/domain/preflight`) : analyse sans rien modifier
   (hostname, FQDN, IP, hosts, DNS sortante, passerelle, ports, horloge, paquets).
5. **Plan** (`confirm=false`) : affiche les 11 étapes sans exécuter.
6. **Exécution** (`confirm=true`) : hostname → `/etc/hosts` → `krb5.conf` →
   secrets (0700) → paquets → arrêt services standalone →
   `samba-tool domain provision` → enable `samba-ad-dc` + attente 389/88/SYSVOL → audit.

**À observer** : chaque étape remonte `{step, status: ok, detail}`.

### 3.3 Vérification de santé
`/identity/health` → **15 vérifications**, `overall` = PASS / WARNING / ERROR :

| Check | Signification |
|---|---|
| hostname / fqdn | nom + résolution du DC |
| samba / ldap / kerberos / dns_port | daemon + ports joignables |
| dns_srv / forward_dns / reverse_dns | enregistrements AD de référence |
| sysvol / netlogon | partages de logon opérationnels |
| keytab | clés dans `secrets.ldb` (modèle Samba, pas de keytab système) |
| krb5_conf / time_sync / ports | configuration, NTP < 5 min, 5 ports AD |

**✅ Exercice 3** — Provisionner si ce n'est pas fait, puis :
- `GET /api/v1/identity/health` → `overall` vaut `PASS` ;
- `GET /api/v1/identity/domain/services` → `samba-ad-dc=active`, `chrony=active` ;
- côté shell (via Proxmox) : `dig @127.0.0.1 -t SRV _ldap._tcp.corp.example.internal`.

---

## Module 4 — Gestion quotidienne (lab, 1h30)

Toute l'offre est sous **/identity** dans l'UI, et sous
`/api/v1/identity/*` en API. Les exemples `curl` supposent un token :

```bash
TOKEN=$(curl -s -X POST http://192.168.10.39:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<voir IDENTIFIANTS.md>"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
H="Authorization: Bearer $TOKEN"; B=http://192.168.10.39:8000/api/v1/identity
```

### 4.1 Organiser avec les OU (`/identity/ous`)
```bash
# OU de niveau racine (pas de parent = DC=corp,DC=example,DC=internal)
curl -s -X POST "$B/ous" -H "$H" -H 'Content-Type: application/json' \
  -d '{"name":"Lab Users"}'
# Sous-OU : parent = DN commençant par OU= et finissant par le domaine
curl -s -X POST "$B/ous" -H "$H" -H 'Content-Type: application/json' \
  -d '{"name":"Stagiaires","parent":"OU=Lab Users,DC=corp,DC=example,DC=internal"}'
```
Règles : `OU_CN_RE` — commence par alphanumérique, `[A-Za-z0-9 ._-]`, 1–65 c. ;
`parent` doit commencer par `OU=` (vide = racine domaine).
Opérations : `POST /ous/move`, `POST /ous/rename`, `DELETE /ous`.

> **Retenir** : une OU est un *dossier* (organisation/GPO) ;
> un groupe est une *liste de comptes* (droits).

### 4.2 Créer des utilisateurs (`/identity/users`)
```bash
curl -s -X POST "$B/users" -H "$H" -H 'Content-Type: application/json' \
  -d '{"username":"jdupont","password":"<8+ car.>","ou":"OU=Lab Users,DC=corp,DC=example,DC=internal"}'
```
Cycle de vie : `PUT /users/{name}` (profil) · `POST …/password` (reset) ·
`…/enable` `…/disable` (compte) · `…/unlock` (verrouillage après échecs) ·
`…/expiry` (expiration) · `DELETE /users/{name}`.
Validation : `ACC_RE` = `[A-Za-z0-9._-]{1,64}` — **pas d'espace ni d'accent**.

### 4.3 Groupes (`/identity/groups`)
```bash
# Créer un groupe avec ESPACE (autorisé — Groupes AD built-in en ont)
curl -s -X POST "$B/groups" -H "$H" -H 'Content-Type: application/json' \
  -d '{"name":"Lab Admins","description":"Administrateurs du lab"}'
# Ajouter / retirer des membres (add[] / remove[])
curl -s -X POST "$B/groups/Lab%20Admins/members" -H "$H" \
  -H 'Content-Type: application/json' -d '{"add":["jdupont","lab.user"],"remove":[]}'
# Lire un groupe built-in
curl -s "$B/groups/Domain%20Admins" -H "$H"
```
→ Règle `GROUP_RE` : 1–64 c., lettres/chiffres puis `[A-Za-z0-9 ._-]`.

### 4.4 Ordinateurs (`/identity/computers`)
```bash
curl -s -X POST "$B/computers" -H "$H" -H 'Content-Type: application/json' \
  -d '{"name":"WS01"}'          # compte machine WS01$ créé
curl -s -X POST "$B/computers/WS01/disable" -H "$H"   # révoquer l'accès réseau
```

### 4.5 Politiques de mots de passe (`/identity/policies`, §14)
```bash
curl -s "$B/policies" -H "$H"                          # lecture (samba-tool domain passwordsettings)
curl -s -X PUT "$B/policies" -H "$H" -H 'Content-Type: application/json' \
  -d '{"min_pwd_length":12,"history_length":5,"account_lockout_threshold":5,"account_lockout_duration":30}'
```
Bornes : longueur 0–128 · historique 0–24 · verrouillage 0–999 tentatives /
durée 0–999 min · complexité on/off. Champs : `complexity`,
`history_length`, `min_pwd_length`, `min_pwd_age`, `max_pwd_age`,
`account_lockout_duration`, `account_lockout_threshold`,
`reset_account_lockout_after` (tous optionnels — on n'envoie que ceux qu'on change).

**✅ Exercice 4** — Créer l'arborescence `OU=Lab Users` + `OU=Lab Machines`,
un utilisateur `jdupont` dans `Lab Users`, le groupe `Lab Admins` (avec espace),
ajouter `jdupont` comme membre, appliquer min 12 car. + lockout 5,
puis vérifier `GET /identity/audit` que les events `identity.*` ont `result=SUCCESS`.

---

## Module 5 — DNS Active Directory (45 min)

### Pourquoi AD a besoin de DNS
Les clients trouvent le DC via des **enregistrements SRV** publiés par Samba :

| Record | Rôle |
|---|---|
| `_ldap._tcp` / `_kerberos._tcp` | localisation DC (LDAP/KDC) |
| `A infraos-dev` | adresse du DC (192.168.10.39) |
| `PTR` (reverse) | résolution inverse — santé `reverse_dns` |

### Vérifier (sans privilège AD — le DNS AD est non-authentifié par protocole)
```bash
dig @127.0.0.1 -t SRV _ldap._tcp.corp.example.internal
dig @127.0.0.1 corp.example.internal A
dig @127.0.0.1 -x 192.168.10.39          # reverse
```
Ou via l'UI : **/identity/dns** · API : `GET /identity/domain/dns`,
`GET /identity/test/dns`.

> ⚠️ **Piège pédagogique** : `samba-tool dns` (RPC) exige un ticket Kerberos
> (`NT_STATUS_LOGON_FAILURE` sinon). D'où l'usage de `dig` dans InfraOS —
> la lecture DNS est ouverte par protocole, l'**écriture** reste protégée
> (seuls les comptes autorisés publient des records, via l'API/`dnstools`).

**✅ Exercice 5** — Depuis le DC : lister tous les records de la zone,
confirmer le SRV vers `infraos-dev.corp.example.internal`, puis vérifier
`GET /identity/health` → `dns_srv = PASS`.

---

## Module 6 — Jointure des postes (45 min)

### Windows
1. Poste en DNS = **192.168.10.39** (le DC) — `ipconfig /all`.
2. Paramètres → Système → Info → « Rejoindre un domaine » → `corp.example.internal`.
3. Compte `Administrator` du domaine (mot de passe AD).
4. Vérifier : `systeminfo | findstr /B "Domain"` puis `gpupdate /force`.
   → UI InfraOS : page **/identity/join** (aide-mémoire + diagnostics).

### Linux (realmd + sssd + adcli)
```bash
realm discover corp.example.internal
realm join corp.example.internal -U 'Administrator'   # (mot de passe AD)
id jdupont                                            # compte AD résolu
```

### Tester l'authentification Kerberos (sans poste)
```bash
# UI : /identity/kerberos  —  API : POST /identity/test/kerberos
curl -s -X POST "$B/test/kerberos" -H "$H" -H 'Content-Type: application/json' \
  -d '{"username":"lab.user","password":"<voir IDENTIFIANTS.md>"}'
# → {"kinit":"OK"}  (le ticket TGT est obtenu puis détruit)
```

**✅ Exercice 6** — `kinit` OK pour `lab.user` ET pour `Administrator` ;
si échec : vérifier l'horloge (`GET /identity/domain/time`, dérive < 5 min)
et le DNS du client.

---

## Module 7 — Santé, audit, sauvegarde (45 min)

### Les pages de surveillance (UI)
| Page | API | Contenu |
|---|---|---|
| `/identity/health` | `GET /health` | 15 checks, `overall` |
| `/identity/kerberos` | `GET /domain/kerberos` | realm, KDC, statut |
| `/identity/ldap` | `GET /domain/ldap` | annuaire joignable |
| `/identity/dns` | `GET /domain/dns` | zones + records |
| (services) | `GET /domain/services` | §19 : samba-ad-dc, smbd, chrony… |
| (temps) | `GET /domain/time` | §18 : NTP, horloge, dérive |
| `/identity/audit` | `GET /audit` | events `identity.*` filtrables |

### Audit
```bash
curl -s "$B/audit?limit=20" -H "$H"
# Chaque événement : actor, action (identity.user.created…), detail, result SUCCESS/FAILURE
```
Une **FAILURE** (ex. nom de groupe invalide) reste tracée — c'est voulu.

### Sauvegarde & restauration (§29)
```bash
# Backup AD (tar de /var/lib/samba/private + SYSVOL)
curl -s -X POST "$B/domain/backup" -H "$H"
# → /var/backups/infraos/samba-identity-<stamp>.tar.gz (0600)
```
- `DELETE /identity/domain` sans `confirm` = avertissement + plan ; avec
  `confirm=true` = backup puis état `ready_for_uninstall`.
- Désinstallation module : **409** si domaine provisionné sans `confirm=true`,
  et les paquets Samba/Kerberos ne sont **jamais** retirés (`keep_packages`).

**✅ Exercice 7** — Lancer un backup, relever le chemin du fichier,
consulter les 10 derniers événements d'audit.

---

## Module 8 — Dépannage (30 min)

| Symptôme | Cause | Solution |
|---|---|---|
| Provision : `token stack underflow` | LXC **unprivileged** | CT privilégié (voir IDENTITY.md) |
| `chronyd : adjtimex failed` | `CAP_SYS_TIME` absente | patch hôte `common.conf` (retirer `sys_time` du drop) |
| `resolv.conf` = `localdomain` au boot | DHCP qui réécrit | IP **statique** du DC |
| `samba-tool dns` → `NT_STATUS_LOGON_FAILURE` | RPC sans ticket | utiliser `dig @127.0.0.1` (lecture) |
| `kinit` : `Clock skew too great` | horloge > 5 min | `GET /domain/time`, corriger NTP (chrony) |
| Client ne joint pas / `nom inconnu` | client sans DNS=DC | mettre 192.168.10.39 en DNS primaire |
| Groupe refusé (400) | espace/caractère invalide | `GROUP_RE` : `[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}` |
| `forward_dns` WARNING | forwarder LAN/défaillant | vérifier `dns forwarder` dans smb.conf |
| Health `dns_srv` ERROR | SRV pointe vers mauvais hôte | reprovision avec nom court (15 c. max NetBIOS) |
| Services smbd/nmbd `inactive` | auto-exclus en mode AD | normal (condition Debian) — ne pas forcer |

**Commandes de diagnostic express** (côté DC) :
```bash
systemctl status samba-ad-dc chrony
dig @127.0.0.1 -t SRV _ldap._tcp.corp.example.internal
klist -k 2>/dev/null || echo "cles dans secrets.ldb (Samba)"
samba-tool domain info localhost    # résumé DC (en root)
```

---

## Module 9 — Bonnes pratiques (30 min)

1. **Mots de passe** : minimum 12 car. dans le lab ; politiques AD (§14)
   verrouillage 5 essais / 30 min ; jamais de mot de passe dans l'UI d'InfraOS
   pour le compte `admin` (à noter hors dépôt, ex. gestionnaire de mots de passe).
2. **Domain Admins au plus petit** : 1–2 comptes dédiés ; le reste en
   groupes fonctionnels (`Lab Admins` d'où le droit *délégué*).
3. **Comptes machine** : désactiver (`/computers/{name}/disable`) tout poste
   retiré du réseau.
4. **Audit** : parcourir régulièrement `GET /audit` ; les FAILURE = tentative
   ou erreur à investiguer.
5. **Backup** : backup AD **avant** toute jointure/réplication à grande échelle ;
   snapshots LXC avant provision.
6. **Pas de secret en base** : ne jamais coller un mot de passe dans un
   `description`, un share ou un ticket — l'UI masque, PostgreSQL n'en stocke pas.
7. **DNS** : le DC est pointeur unique — avant de changer son IP, mettre à jour
   le record `A` + le forwarder.

---

## Évaluation — validation des acquis

### Quiz (corrigé ci-dessous)
1. LDAP et Kerberos tournent sur quels ports ?
2. Pourquoi provisionner avec un nom d'hôte **court** (≤ 15 c.) ?
3. Quelle est la différence entre `GET /ous` et `GET /groups` ?
4. Que retourne `DELETE /identity/domain` **sans** `confirm` ?
5. Un utilisateur peut-il créer un groupe nommé `Ops ?` — pourquoi ?
6. Comment vérifier la santé AD en une commande ?
7. Pourquoi `samba-tool dns` échoue-t-il en tant que root sans ticket ?

### Exercice pratique final (checklist)
- [ ] Preflight `PASS` sans erreur bloquante
- [ ] `overall` santé = **PASS** (15/15)
- [ ] OU `Lab Users` créée + utilisateur dedans
- [ ] Groupe `Lab Admins` (espace) avec ≥ 1 membre
- [ ] `POST /test/kerberos` → OK pour 2 comptes
- [ ] Politique : min 12 + lockout 5 appliquée
- [ ] Backup AD généré (chemin relevé)
- [ ] Audit : ≥ 6 events `identity.*` en SUCCESS

### Corrigé du quiz
1. LDAP : **389** ; Kerberos : **88**. — 2. NetBIOS/NetBT tronque à 15 c. ; un
nom plus long casse les SRV (`INFRAOS-DEV.COR` → record A inexistant).
3. `ous` = arborescence LDAP (dossiers) ; `groups` = listes de comptes.
4. Il renvoie l'**avertissement + le plan** de suppression, sans rien faire.
5. Non — `?` est interdit : `GROUP_RE` = `^[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}$`
   (l'espace *interne* est permis, pas les autres caractères).
6. `curl …/api/v1/identity/health` (ou page `/identity/health`).
7. La RPC `samba-tool dns` exige un ticket Kerberos ; sans kinit →
`NT_STATUS_LOGON_FAILURE` (d'où `dig` pour la lecture dans InfraOS).

---

## Glossaire express

**AD** Active Directory · **DC** Domain Controller · **OU** Organizational Unit ·
**GPO** Group Policy Object · **SPN** Service Principal Name · **TGT** Ticket
Granting Ticket (kinit) · **SYSVOL** partage des GPO · **NETLOGON** partage de
logon · **DN / CN / DC** chemin LDAP · **RID/SID** identifiants de sécurité ·
**RODC** DC en lecture seule (prévu, non implémenté) · **NTLM** protocole
d'auth historique (Kerberos préféré).

## Annexes — ressources

| Ressource | Lien |
|---|---|
| Spécifications module | `docs/IDENTITY.md` |
| Guide UI (section Identité) | `docs/GUIDE-UTILISATION.md` |
| Stratégie AD InfraOS | `docs/DOMAIN.md` |
| Identifiants lab (local) | `docs/IDENTIFIANTS.md` |
| API complète | http://192.168.10.39:8000/docs |
| Smoke test | `bash scripts/test/check-lxc.sh root@192.168.10.90 133 http://192.168.10.39:8000` |

### Correspondance UI ↔ API ↔ samba-tool

| Action | UI | API | samba-tool (équivalent) |
|---|---|---|---|
| Provision | `/identity/domain` | `POST /domain/setup` | `domain provision` |
| Santé | `/identity/health` | `GET /health` | — |
| Utilisateur | `/identity/users` | `POST /users` | `user create` |
| Groupe | `/identity/groups` | `POST /groups` | `group create` |
| OU | `/identity/ous` | `POST /ous` | `ou create` |
| Machine | `/identity/computers` | `POST /computers` | `computer create` |
| Politiques | `/identity/policies` | `PUT /policies` | `domain passwordsettings set` |
| Backup | — | `POST /domain/backup` | (tar privé) |
