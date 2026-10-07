# Stack technique InfraOS (point 4)

| Couche | Choix | Paquet Debian 13 / pip | État |
|--------|-------|------------------------|------|
| OS | Debian 13 Trixie | template `debian-13-standard_13.1-2` | LXC 133 actif |
| Backend | Python 3.13 | `python3` natif | OK |
| API | FastAPI + Uvicorn | pip | OK (`/docs`) |
| Validation | Pydantic v2 | pip | OK |
| ORM | SQLAlchemy 2.x | pip | nouveau |
| Migrations | Alembic (`core/alembic/`, `0001_init`) | pip | nouveau |
| DB prod | PostgreSQL 16 | `postgresql` (ISO + LXC) | script `init-postgres.sh` |
| DB dev | SQLite | stdlib sqlite | défaut |
| Cache/jobs | Redis 7 (+fallback mémoire) | `redis-server` | nouveau, optionnel |
| Frontend | React 18 + TS + Vite 5 + Tailwind 3 | npm | OK + page Login |
| Auth | locale JWT (PBKDF2) ; LDAP/AD/Kerberos stubs | `python-jose` | nouveau |
| Natifs | systemd, apt, dpkg, journald, nftables, iproute2 | via `exec.py` allow-list | `test_native.py` |

SQLite par défaut (zéro friction dev) ; Postgres dès que `INFRAOS_DB_URL`
pointe dessus (`postgresql+psycopg2://...`). Redis idem avec `INFRAOS_REDIS_URL`.
