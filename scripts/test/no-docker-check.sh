#!/bin/bash
# Prouve que le projet fonctionne sans Docker (dependance interdite en dev).
# Usage: bash scripts/no-docker-check.sh root@192.168.10.90 133
set -u
HOST="${1:-root@192.168.10.90}"
CT="${2:-133}"
echo "== Docker absent du LXC $CT (attendu) =="
ssh -o StrictHostKeyChecking=no "$HOST" "pct exec $CT -- bash -c 'which docker && echo DOCKER_FOUND_KO || echo NO_DOCKER_OK; dpkg -l 2>/dev/null | grep -i docker && echo DOCKER_PKG_KO || echo NO_DOCKER_PKG_OK; systemctl is-active infraos-api; curl -s http://127.0.0.1:8000/api/health'" 2>&1
echo ""
echo "== Aucune reference Docker obligatoire dans le code (attendu: vide ou docs seulement) =="
grep -ri "docker" --include="*.py" --include="*.sh" --include="Makefile" backend frontend agent scripts Makefile 2>/dev/null | grep -vi "no-docker" | head -n 10 || echo "NO_DOCKER_REF_OK"
