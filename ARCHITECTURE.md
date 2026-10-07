# ARCHITECTURE InfraOS — pensée LXC -> ISO dès le jour 1

## 1. Objectif
OS serveur administrable via Web centralisée : users/groupes, domaine,
DNS, DHCP, réseau, firewall, VPN, IPAM, découverte, monitoring, fichiers,
sauvegardes, logs/sécurité, updates, modules, état services.

## 2. Règle d'or : pas de LXC -> ISO
- **LXC 132 = dev/test uniquement.** Pratique (snapshot, clone, `pct exec`),
  mais noyau partagé, pas de firewall/VPN kernel full, pas de bootloader.
- **ISO = build reproductible** : `mmdebstrap`/`live-build` partant de
  `debian-13-trixie` netboot + liste de paquets + `infraos-*.deb` + preseed.
- Conséquence : **tout le code doit être agnostique du runtime.**
  Détection via `systemd-detect-virt` + capabilities, jamais de chemin en dur LXC.

```
infraos-core  (python lib, sans hypothèse LXC/bare-metal)
     │
     ├─▶ adapters: SystemdAdapter, AptAdapter, NetworkAdapter (netlink/ip),
     │             DnsAdapter(BIND9), DhcpAdapter(Kea), NftAdapter, WgAdapter,
     │             SambaAdapter, StorageAdapter
     │
infraos-api   (FastAPI, JWT, RBAC admin/opérateur/lecture)
     │  REST /api/v1/... + OpenAPI
     ▼
infraos-ui    (React, appels API uniquement, jamais de ssh direct)
```

## 3. Couches

### 3.1 core/infraos
- `config.py` : `/etc/infraos/config.yaml` + env `INFRAOS_*`
- `db.py` : SQLite par défaut (`/var/lib/infraos/infraos.db`), Postgres optionnel
- `module_base.py` : classe `InfraModule` (manifest, install/configure/status/enable)
- `system/` : `os_info`, `systemd` (list/start/stop via dbus ou `systemctl`),
  `apt` (updates), `network` (lecture `/sys`, `ip`, `nmcli`/`systemd-networkd`)
- `detect.py` : `virt = systemd-detect-virt`, `is_container`, capabilities firewall

### 3.2 api/
FastAPI. Auth JWT local (admin initial créé au bootstrap, mot de passe à changer).
RBAC simple. Chaque domaine métier = router.
Pas de commande shell aveugle : tout passe par core avec allow-list.

Routes v1 MVP :
- `GET /api/health`, `GET /api/v1/system/info`, `GET /api/v1/services`
- `GET/POST /api/v1/modules`, `GET /api/v1/network/interfaces`
- `GET/POST /api/v1/users` (système local d'abord, LDAP/AD en phase 2)

### 3.3 ui/
React + Vite + Tailwind. Pages : Dashboard (état services), Système, Réseau,
Utilisateurs, Modules, Logs, Mises à jour. Client `src/lib/api.ts` avec token JWT.
Build statique servi par nginx en prod ISO (`/usr/share/infraos/ui`), proxy `/api` → 8000.

### 3.4 modules/
Contrat `manifest.yaml` :
```yaml
name: dns
version: 0.1.0
title: DNS
description: Serveur BIND9
services: [named]
packages: [bind9]
ports: [53/tcp, 53/udp]
requires: [network]
container_support: partial  # ex. firewall/vpn limités en LXC non-privilégié
```
Le backend découvre les manifests au démarrage. Activation = apt install + template
+ systemctl enable. Toute config générée via Jinja, versionnée, rollback possible.

Ordre implémentation : users-groups → network → services-status → updates →
dns → dhcp → firewall → vpn → fileshare → domain → ipam/netdiscovery →
monitoring → backup → logs.

### 3.5 Packaging Debian
- `infraos-core`, `infraos-api`, `infraos-ui`, `infraos-modules-*` en `.deb`
- Installés dans LXC via `pip`/`dpkg -i` en dev, via APT en ISO.
- Fichiers : `/opt/infraos/`, `/etc/infraos/`, `/var/lib/infraos/`,
  `/usr/share/infraos/ui`, `infraos-api.service`.

### 3.6 ISO Builder
`iso/` :
- `packages.list` : debian-base + bind9, kea, nftables, wireguard, samba, etc.
- `preseed/` : installation auto FR, partitionnement guidé, user `infraos-admin`
- `includes/` : overlay `/etc/infraos`, wallpaper, motd
- `build.sh` : live-build sur builder Debian 13 (VM dédiée, pas le LXC),
  sortie `infraos-13.x-amd64.iso` testable sur Proxmox VM (SeaBIOS/OVMF), bare-metal, VPS.
- Étapes : `lb config` → `lb build` → test boot VM → publish checksum.

## 4. Environnements
| Env | Rôle | Notes |
|-----|------|-------|
| LXC 132 (192.168.10.50) | dev/test | snapshot avant chaque module, nesting=1, unprivileged |
| Builder ISO (VM Debian 13) | build ISO | 4CPU/8Go/50Go, accès internet, live-build |
| VM test Proxmox | validation ISO | boot ISO, install, check API/UI |
| Bare-metal / VPS | cible finale | même ISO ou image cloud |

## 5. Sécurité
- API localhost par défaut + nginx TLS (self-signed puis Let's Encrypt/CA interne)
- JWT court + refresh, audit log `/var/log/infraos/audit.log`
- Aucun mot de passe en clair, secrets en `0600`, sudoers minimal via groupe `infraos-admin`
- Firewall deny-by-default en ISO, LXC en mode dégradé documenté.

## 6. Principes dev
- Idempotent : chaque script peut être relancé sans casser.
- Testable : `pytest core/tests`, `make check` sur LXC.
- Observabilité : `/api/health`, journald, `infraos-cli status`.
