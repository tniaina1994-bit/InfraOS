# Guide d'utilisation — Interface Web InfraOS

> Pour l'administrateur système/réseau. Chaque section = **mini-formation**
> sur le service + **pas-à-pas** dans l'interface.
> Accès : `http://192.168.10.39/` (prod LXC) ou `http://localhost:5173` (dev).
> Connexion : page **Connexion** — `admin` / `InfraOS-Admin-2026!`
> (changez-le : **Identité** → votre compte → nouveau mot de passe via l'API ;
> politique : 12 caractères + 1 chiffre minimum).
> Le menu de gauche n'affiche que vos modules **activés et autorisés**.

---

## 1. Dashboard (Vue d'ensemble)

**C'est quoi :** vitrine santé : version, hôte, OS, CPU/RAM/disque, réseau,
services actifs, modules, santé globale, mises à jour, échecs de connexion.
**Lire :** vert = OK, jaune/rouge = agir (cliquez la page concernée).
**Réflexe quotidien :** 30 secondes ici chaque matin.

## 2. Système (Système)

**Mini-formation :** `systemd` pilote les services (`is-active`), les
métriques viennent du noyau (CPU/RAM/disque).
**Santé :** 5 contrôles (base, cache, disque <90 %, mémoire <95 %, services
critiques ssh + infraos-api). `degraded` → lisez le détail.
**Services :** boutons **start / restart / stop** (admin, audités).
⚠️ Ne stoppez jamais `infraos-api` ni `ssh` à distance sans console Proxmox.
**Informations :** hôte, noyau, arch, Python, virtualisation, espace libre.

## 3. Monitoring (Système)

**Mini-formation :** `psutil` lit `/proc` (CPU, mémoire, disque, réseau,
charge, processus, uptime) + capteurs (`acpitz`).
**Utiliser :** **Enregistrer un échantillon** fige une mesure ;
l'historique donne les 20 dernières (courbes à venir).
**Agents :** un PC/serveur distant avec `agent/` remonte ici
(`docs/AGENT.md`) : enregistrez-le (hostname + token 32+ car.), il push
toutes les 60 s. `last_seen` = fraîcheur.

## 4. Mises à jour (Système)

**Mini-formation :** InfraOS utilise **APT/Debian** (jamais réinventé).
**Utiliser :** tableau des paquets → **Installer** unitairement (admin,
audité, historisé) ; **Historique** = qui a installé quoi et quand.
💡 Sécurité d'abord : traitez les paquets `security` en priorité.

## 5. Logs (Système)

**Mini-formation :** `journald` centralise les logs ; l'audit InfraOS
(user/action/ressource/IP/résultat) est en plus en base.
**Utiliser :** filtrez la piste d'audit (rouge = FAILURE/DENIED), lisez
`infraos-api` en dessous. Rétention : rotation automatique.

## 6. Réseau (Réseau)

**Mini-formation :** `ip addr/route` (lecture), passerelle = route `default`,
résolveur = `/etc/resolv.conf`.
**Utiliser :** vérifiez interfaces UP + IPv4 + route par défaut avant toute
chose. **VLAN :** `eth0` + ID (1-4094) → **Préparer** stage les fichiers
systemd-networkd **sans reload** (appliquez ensuite en console si besoin).
⚠️ Ne touchez pas à l'interface de production sans `confirm` et backup.

## 7. DNS (Réseau — BIND9)

**Mini-formation :** zone = portion d'espace de noms (`lan.local`) ;
records : **A** (IPv4), **AAAA** (IPv6), **CNAME** (alias, exclusif),
**MX** (mail + priorité), **TXT** (SPF…), **NS** (serveurs), **PTR**
(reverse `in-addr.arpa`). Sérial auto.
**Utiliser :** **Créer** la zone → cliquez-la → **Ajouter** les records →
**Appliquer (BIND9)** (`named-checkconf` obligatoire puis `rndc reload`).
Testez : `dig @192.168.10.39 srv.lan.local A`.
Forwarders globaux : serveurs DNS amont (ex. `192.168.10.252`).

## 8. DHCP (Réseau — Kea)

**Mini-formation :** scope = sous-réseau + plage (pool) + options
(passerelle/routers, DNS, domaine, durées de bail) ; réservation =
MAC → IP fixe (serveurs, imprimantes).
**Utiliser :** **Créer** le scope (ex. `192.168.0/24`, pool `.100-.200`,
gateway `.254`) → réservations → **Appliquer (Kea)** (`kea-dhcp4 -t`
puis restart). **Baux** = qui a reçu quoi.
⚠️ Un seul DHCP par segment ! Désactivez la box/routeur avant.

## 9. Découverte (Réseau — nmap)

**Mini-formation :** scan `ping` = ARP/ICMP (hôtes + MAC), `fast` = ports
courants, `os` = empreinte OS (1 hôte).
**Utiliser :** cible `192.168.10.0/24` (jamais `0.0.0.0/0`, CIDR ≥ /16) →
**Scanner** (admin, audité) → comparez avec **Voir** les scans précédents
(new/gone/changed = arrivées/départs/modifs).

## 10. IPAM (Réseau)

**Mini-formation :** inventaire : réseau (CIDR) → passerelle réservée →
hôtes (IP/MAC/nom/type). Fini les tableurs d'IP.
**Utiliser :** **Créer** le réseau (ex. `lan20` 192.168.20.0/24 + `.254`) →
cliquez → **Allouer** (première IP libre, gateway exclue).
Barre = taux de remplissage. Liens DNS/DHCP : phase suivante.

## 11. Firewall (Sécurité réseau — nftables)

**Mini-formation :** chaînes `input` (vers le serveur), `forward` (traversant),
`output`, `prerouting`/`postrouting` (NAT). Verdicts : accept/drop/dnat
(redirection)/masquerade (partage de connexion)/log.
**Utiliser :** **Ajouter** (ex. input/accept/tcp/443) → **Appliquer (nft)**
(`nft -c` bloque toute règle invalide avant application).
DNAT : `prerouting` + `nat_to=192.168.20.10:8080`.
⚠️ Politiques par défaut `accept` en dev ; passez en `drop` + règles
explicites en production.

## 12. VPN (Sécurité réseau — WireGuard)

**Mini-formation :** tunnel chiffré à clés (privée 0600 jamais exposée,
publique échangée) ; `AllowedIPs` = ce qui passe dans le tunnel ;
`Endpoint` = où joindre le pair ; keepalive = maintien NAT.
**Utiliser :** **Créer wg0** (`10.8.0.1/24`, clés auto) → ajoutez le pair
(`generate_key` ou collez sa publique, `10.8.0.2/32`) → **Appliquer**.
Donnez au pair la conf client (adresse `.2/24`, peer = publique serveur +
`Endpoint <ip-publique>:51820`).

## 13. Sécurité (Sécurité réseau — journald)

**Mini-formation :** fail2ban bannit les IP après N échecs (jails),
Suricata inspecte le trafic (eve.json), rsyslog centralise.
**Utiliser :** compteurs (échecs 24h, alertes, updates), liste bruteforce
(≥5 échecs/IP/15 min), échecs récents avec IP, intégrations
(journald actif, autres `planned`). Réaction : bannissez l'IP au firewall
ou durcissez les mots de passe.

## 14. Identité (Annuaire & partage)

**Mini-formation :** rôles `superadmin > admin > operator > readonly` ;
rôle **effectif** = max(rôle user, rôles groupes) ; on ne donne jamais un
rang ≥ au sien ; LDAP/AD/Kerberos branchés en phase 2 (stubs `501`).
**Utiliser :** créez l'utilisateur (mdp 12 car. + chiffre) →
créez le groupe (rôle conféré, ex. `ops`/operator) → ajoutez-y le membre
(le rôle effectif monte). **Désactiver** plutôt que supprimer (audit gardé).
Jamais d'auto-désactivation.

## 15. Fichiers (Annuaire & partage — Samba)

**Mini-formation :** partage = `[nom]` + chemin + droits (valid users `@groupes`,
read only, guest). `testparm` valide avant reload.
**Utiliser :** **Créer** (`docs` → `/srv/docs`, dossier auto-créé) →
**Appliquer (Samba)** → testez `smbclient -L //192.168.10.39 -N`.
AD : `security = ADS` prévu au provisionnement du domaine.

## 16. Sauvegardes (Protection — restic/borg/rsync)

**Mini-formation :** restic/borg = chiffrés + dédupliqués + rétention
(`--keep-daily/weekly`), rsync = miroir simple. Mot de passe en
`/etc/infraos/backup-pw/` (0600, jamais en base).
**Utiliser :** **Créer** le job (moteur + dépôt + sources absolues) →
**Exécuter** → **Runs** (statut + logs). **Restauration** admin uniquement,
cible restreinte (`/var/lib/infraos/restore/`, `/tmp/`).
Planifiez via `POST /backup/cron/apply` + script worker à venir.

## 17. Modules (Administration)

**Mini-formation :** monolithe modulaire : manifeste (paquets/services/
dépendances) + backend ; ordre de démarrage topo ; état persistant.
**Utiliser :** **Activer/Désactiver** (dépendances auto-activées, refus si
requis par un actif), **Désinstaller** (paquets retirés, confirm).
Page Modules = interrupteurs de tout l'OS.

## 18. Paramètres (Administration)

**Mini-formation :** `/etc/infraos/infraos.yaml` (canonique) ; secrets
caviardés (`***`), jamais en base ; `modules/<m>.yaml` par module.
**Utiliser :** lisez la config effective, réglez la durée de session JWT,
structure visible en bas. Secrets : API dédiée (jamais affichés).

---

## Conduite à tenir (rappels)

1. **Dashboard** chaque matin (santé, updates, échecs login).
2. Toute écriture sensible = **admin**, **auditée** (Logs).
3. Jamais de shell libre : tout passe par allow-list validée.
4. Testez (`dig`, `kea -t`, `testparm`, `nft -c`) — l'**Appliquer** le fait pour vous.
5. Sauvegardez avant de toucher réseau/firewall.
