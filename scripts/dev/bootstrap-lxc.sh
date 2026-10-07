#!/bin/bash
# Push dev rapide du nouveau layout vers /opt/infraos (iterations, pas install).
# Pour une installation complete : scripts/install/bootstrap.sh
# Usage: bash scripts/dev/bootstrap-lxc.sh [root@192.168.10.90] [133]
set -euo pipefail
HOST="${1:-root@192.168.10.90}"
CT="${2:-133}"

tar --exclude='__pycache__' --exclude='*.pyc' \
  -czf /tmp/infraos-code.tgz backend modules docs scripts config installer
scp -o StrictHostKeyChecking=no /tmp/infraos-code.tgz "$HOST:/tmp/infraos-code.tgz"
ssh -o StrictHostKeyChecking=no "$HOST" \
  "pct push $CT /tmp/infraos-code.tgz /tmp/infraos-code.tgz && pct exec $CT -- bash -c 'tar --no-same-owner -xzf /tmp/infraos-code.tgz -C /opt/infraos && cp /opt/infraos/installer/systemd/infraos-api.service /etc/systemd/system/ && systemctl daemon-reload && systemctl restart infraos-api && sleep 3 && curl -s http://127.0.0.1:8000/api/health && echo PUSH_OK'"
