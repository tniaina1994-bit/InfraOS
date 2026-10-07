# InfraOS — Infrastructure Server OS

Alternative 100% gratuite et open source (inspirée fonctionnellement de Zentyal, code indépendant)
pour administrer un serveur d'infrastructure depuis une interface Web centralisée.

**Base : Debian 13 (trixie) — Backend : Python FastAPI — Frontend : React + Vite + Tailwind**

## Principe fondamental

> LXC `infraos-dev` Debian 13 sur Proxmox (CT 133 @ 192.168.10.39) est **uniquement**
> l'environnement de **développement / test** (legacy CT 132 `InfraOS` @ .50 conservé).
>
> On ne transforme **jamais** un LXC en ISO.
> L'ISO InfraOS est construite de façon **reproductible** à partir de paquets Debian 13
> + paquets InfraOS (`.deb`) + installeur, via `iso/` (live-build).
> Le même code tourne sur LXC (dev), VM, bare-metal et cloud.
>
> **Sans Docker :** 100% natif systemd + pip + nginx. Docker n'est ni requis ni utilisé.

```
┌──────────────┐      ┌──────────────┐      ┌───────────────┐
│ LXC 133      │      │  VM / Bare   │      │  ISO InfraOS  │
│ infraos-dev  │ ───▶ │  Metal / VPS │ ◀─── │  (live-build) │
│ 192.168.10.39│      │              │      │               │
│ natif, no    │      │  même .deb   │      │  debian-13 +  │
│ Docker       │      │  natif       │      │  infraos-*    │
└──────────────┘      └──────────────┘      └───────────────┘
       ▲                    ▲
       └──────── même code ─┘
       backend/ + frontend/ + modules/ (systemd, pas Docker)
```

## 2. Environnement de développement initial (spec officielle)

Hyperviseur : Proxmox VE 9.2.

| Param | Valeur |
|-------|--------|
| CT ID | 133 |
| Hostname | infraos-dev |
| OS template | debian-13-standard_13.1-2_amd64.tar.zst (Trixie) |
| Type | LXC non privilégié (`unprivileged=1`) |
| CPU | 4 vCPU |
| RAM | 8 GB |
| Swap | 2 GB |
| Disk | 40 GB (local-lvm) |
| Network | vmbr0, dhcp (192.168.10.39) |
| Features | nesting=1 |
| Docker | **interdit** — `which docker` → absent, API via systemd+pip |

```bash
make create-lxc LXC_ID=133        # cree le CT si absent (idempotent)
make provision LXC_ID=133 API_URL=http://192.168.10.39:8000
make check LXC_ID=133 API_URL=http://192.168.10.39:8000
make no-docker-check LXC_ID=133   # prouve 0 dependance Docker
```

## Démarrage rapide

### 1. Prérequis (poste Windows)
- SSH : `ssh root@192.168.10.90` (clé OK)
- Proxmox 9.2 + CT 133 `infraos-dev` running (Debian 13, 192.168.10.39, natif sans Docker)

### 2. Provisionner le LXC dev
```bash
make provision   # -> scripts/install/bootstrap.sh via ssh + pct exec 133
make check       # -> health API + os-release
```

### 3. Dev local (sans Proxmox)
```bash
# backend
pip install -e backend/.[dev,postgres] && cd backend/app
uvicorn main:app --reload --port 8000

# frontend
cd frontend && npm install && npm run dev
# UI -> http://localhost:5173, API -> http://localhost:8000
```

### 4. Construire l'ISO (plus tard, sur builder Debian 13 dédié)
```bash
make iso   # -> iso/build.sh (live-build, reproductible)
```

## Modules (v1 roadmap)
identity (utilisateurs/groupes), system, domain (Samba AD), dns (BIND9), dhcp (Kea/ISC), network,
firewall (nftables), vpn (WireGuard), ipam, netdiscovery, monitoring,
fileshare (Samba), backup (Restic/Borg), logs, updates, modules-manager, services-status.

Chaque module = `modules/<nom>/manifest.yaml + backend python + routes API + page UI`.
Voir `modules/README.md` et `ARCHITECTURE.md`.

## Structure finale
```
infraos/
├── backend/app/   -> main.py, api/ (routers), core/infraos/ (managers, exec, db)
├── backend/tests/ -> 138 tests pytest · backend/alembic/ (migrations 0001→0013)
├── frontend/      -> React+TS+Vite+Tailwind (19 pages)
├── core/          -> *-manager/ (contrats composants)
├── modules/       -> 19 manifests + backends (identity→certificates)
├── agent/         -> client Python Linux/Windows + protocole
├── config/        -> default-config.yaml (template /etc/infraos/)
├── scripts/      -> install/ (bootstrap.sh, init-postgres.sh) · dev/ · test/ · build/ · iso/
├── packaging/    -> debian/ (.deb infraos-*)
├── installer/    -> systemd unit + nginx (+ TLS prêt)
├── iso/          -> live-build + preseed -> ISO installable
├── docs/         -> 25+ guides (ARCHITECTURE, SECURITY, API...)
└── tests/        -> tests e2e/fumée
```

## Documentation

- **Guide d'utilisation** : `docs/GUIDE-UTILISATION.md` (interface Web,
  configuration de chaque service + mini-formations)
- Architecture, sécurité, API : `docs/` (25+ guides)

## Licence

GPLv3 — 100% gratuit et open source, aucun composant propriétaire obligatoire.
Voir `LICENSE`, `docs/PHILOSOPHY.md` (14 principes → preuves) et `docs/SECURITY.md`.
