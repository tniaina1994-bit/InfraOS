#!/bin/bash
# Verif LXC dev: OS + API health
set -u
HOST="${1:-root@192.168.10.90}"
CT="${2:-132}"
API="${3:-http://192.168.10.50:8000}"
echo "== OS =="
ssh -o StrictHostKeyChecking=no "$HOST" "pct exec $CT -- cat /etc/os-release | head -n 3"
echo "== API $API/api/health =="
curl -s --max-time 5 "$API/api/health" || echo "API KO (normal si bootstrap non lance)"
echo ""
echo "== system/info =="
curl -s --max-time 5 "$API/api/v1/system/info" | head -c 800
echo ""
