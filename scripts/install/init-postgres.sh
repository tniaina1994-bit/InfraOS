#!/bin/bash
# Init Postgres natif InfraOS (LXC Debian 13) + config + migrate + seed.
# A executer DANS le LXC (via pct exec). Idempotent (role/db existants OK).
set -euo pipefail
ADMIN_PW="${INFRAOS_ADMIN_PASSWORD:-InfraOS-Admin-2026!}"

if ! su postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='infraos'\"" | grep -q 1; then
  DBPW=$(openssl rand -hex 16)
  su postgres -c "psql -c \"CREATE ROLE infraos LOGIN PASSWORD '$DBPW'\""
  echo "role infraos cree"
else
  # rotation mdp pour rester reproductible
  DBPW=$(openssl rand -hex 16)
  su postgres -c "psql -c \"ALTER ROLE infraos LOGIN PASSWORD '$DBPW'\""
  echo "role infraos existant (mdp regenere)"
fi
su postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='infraos'\"" | grep -q 1 \
  || su postgres -c "psql -c \"CREATE DATABASE infraos OWNER infraos\""

JWT=$(openssl rand -hex 32)
cat > /etc/infraos/infraos.yaml <<EOF
data_dir: /var/lib/infraos
db_url: postgresql+psycopg2://infraos:$DBPW@127.0.0.1:5432/infraos
redis_url: redis://127.0.0.1:6379/0
jwt_secret: $JWT
jwt_expire_min: 60
admin_user: admin
api_host: 127.0.0.1
api_port: 8000
EOF
chmod 600 /etc/infraos/infraos.yaml
# compat legacy (lu en second) : garde synchronise
cp /etc/infraos/infraos.yaml /etc/infraos/config.yaml
echo CONFIG_OK

export INFRAOS_DB_URL="postgresql+psycopg2://infraos:$DBPW@127.0.0.1:5432/infraos"
cd /opt/infraos/backend
# venv dedie si bootstrap.sh est passe, sinon python systeme
PYBIN=/opt/infraos/venv/bin/python
[ -x "$PYBIN" ] || PYBIN=python3
"$PYBIN" -m alembic -c alembic.ini upgrade head 2>&1 | tail -n 2
export INFRAOS_ADMIN_PASSWORD="$ADMIN_PW"
"$PYBIN" seed_admin.py
echo "POSTGRES_INIT_OK (admin: admin / mot de passe fourni ou InfraOS-Admin-2026!)"
