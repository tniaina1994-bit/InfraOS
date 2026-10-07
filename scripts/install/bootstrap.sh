#!/bin/bash
# ==============================================================================
# InfraOS — scripts/install/bootstrap.sh
# Prepare automatiquement un LXC Debian 13 (template standard) pour InfraOS.
#
# Usage DANS le LXC (root) :  bash /tmp/bootstrap.sh
# Usage via Proxmox :         make provision   (copie + pct exec)
#
# Garanties : idempotent (re-executable sans rien casser), securise
# (pas de mot de passe en dur, permissions 0600/0700), commente, lisible.
# Sans Docker (100% natif Debian).
# ==============================================================================
set -euo pipefail

# --- 0. Pre-requis : root uniquement -----------------------------------------
if [ "$(id -u)" -ne 0 ]; then
  echo "ERREUR: executez en root (pct exec ... -- bash /tmp/bootstrap.sh)"
  exit 1
fi

# --- 1. Systeme : Debian 13 ---------------------------------------------------
if [ ! -f /etc/os-release ]; then echo "ERREUR: /etc/os-release absent"; exit 1; fi
# shellcheck disable=SC1091
. /etc/os-release
if [ "${ID:-}" != "debian" ] || [ "${VERSION_ID:-}" != "13" ]; then
  echo "ERREUR: Debian 13 requis (detecte: ${PRETTY_NAME:-inconnu})"
  exit 1
fi
echo "[1/12] Debian 13 OK : $PRETTY_NAME"

# --- 2. Mises a jour Debian ---------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq 2>&1 | tail -n 1 || true
echo "[2/12] Debian a jour"

# --- 3. Dependances systeme (paquets Debian natifs, jamais de Docker) ---------
apt-get install -y -qq \
  python3 python3-venv python3-pip git curl sudo openssl \
  iproute2 iputils-ping bind9-dnsutils net-tools \
  nftables wireguard-tools \
  postgresql redis-server nginx \
  bind9 kea-dhcp4-server \
  samba smbclient nmap restic borgbackup rsync \
  sqlite3 2>&1 | tail -n 1 || true
echo "[3/12] Dependances installees (idempotent : deja presents = OK)"

# --- 4. Python : version minimale 3.11 ----------------------------------------
PYV=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[4/12] Python $PYV"
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ requis"'

# --- 5. PostgreSQL : demarre + actif ------------------------------------------
systemctl enable --now postgresql 2>&1 | tail -n 1 || true
pg_lsclusters | grep -q online && echo "[5/12] PostgreSQL actif" || { echo "ERREUR postgres"; exit 1; }

# --- 6. Redis : demarre + PONG -------------------------------------------------
systemctl enable --now redis-server 2>&1 | tail -n 1 || true
redis-cli ping | grep -q PONG && echo "[6/12] Redis actif" || { echo "ERREUR redis"; exit 1; }

# --- 7. Node.js/npm : preparation (build frontend separe, optionnel ici) ------
if command -v node >/dev/null 2>&1; then
  echo "[7/12] Node $(node --version) deja present"
else
  echo "[7/12] Node absent du LXC (build frontend sur le poste dev : make build-ui)"
fi

# --- 8. Utilisateur infraos (service futur, moindre privilege documente) ------
if ! id infraos >/dev/null 2>&1; then
  useradd -m -s /bin/bash infraos
  echo "[8/12] Utilisateur infraos cree"
else
  echo "[8/12] Utilisateur infraos existe (conserve)"
fi

# --- 9. Arborescence /opt/infraos + /etc + /var -------------------------------
mkdir -p /opt/infraos/backend /opt/infraos/agent \
         /etc/infraos/modules /etc/infraos/security /etc/infraos/network \
         /etc/infraos/secrets /etc/infraos/backup-pw \
         /var/lib/infraos /var/log/infraos/backups /usr/share/infraos/ui
chmod 700 /etc/infraos/secrets /etc/infraos/backup-pw
echo "[9/12] Arborescence prete (secrets 0700)"

# --- 10. Environnement Python dedie (/opt/infraos/venv, pas de --break) -------
if [ ! -x /opt/infraos/venv/bin/python ]; then
  python3 -m venv /opt/infraos/venv
  echo "[10/12] venv cree"
else
  echo "[10/12] venv existe (conserve)"
fi
/opt/infraos/venv/bin/pip install -q --upgrade pip
/opt/infraos/venv/bin/pip install -q \
  "fastapi>=0.110" "uvicorn[standard]" "pydantic>=2" "pyyaml>=6" "psutil>=5" \
  "python-jose[cryptography]" "python-multipart" "sqlalchemy>=2" "alembic>=1.13" \
  "psycopg2-binary" "redis" "httpx" "pytest"
echo "[10/12] Dependances Python installees dans le venv"

# --- 11. Base PostgreSQL + configuration initiale ------------------------------
# (init-postgres.sh : role/db/mots de passe aleatoires, 0600, idempotent)
if [ -f /tmp/init-postgres.sh ]; then
  bash /tmp/init-postgres.sh 2>&1 | tail -n 2
else
  echo "[11/12] ATTENTION: /tmp/init-postgres.sh absent — DB a initialiser (make db-init)"
fi

# --- 12. Verification services + resume ----------------------------------------
echo "--- services ---"
for s in postgresql redis-server infraos-api nginx named kea-dhcp4-server smbd; do
  printf "%-18s %s\n" "$s" "$(systemctl is-active "$s" 2>/dev/null || echo 'inactif/non-installe')"
done
echo ""
echo "================ RESUME INSTALLATION ================"
echo "OS      : $PRETTY_NAME ($(systemd-detect-virt 2>/dev/null || echo bare-metal))"
echo "Python  : $PYV (venv /opt/infraos/venv)"
echo "PG/Redis: $(pg_lsclusters 2>/dev/null | grep -c online) cluster(s) / $(redis-cli ping 2>/dev/null)"
echo "Code    : /opt/infraos/backend (deployer via make provision)"
echo "API     : systemctl status infraos-api (port 8000)"
echo "Sante   : curl http://127.0.0.1:8000/api/v1/health"
echo "====================================================="
