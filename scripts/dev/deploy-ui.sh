#!/bin/bash
# Deploie le frontend builde vers le LXC (purge complete anti-bundles obsoletes).
# Usage: bash scripts/dev/deploy-ui.sh [root@192.168.10.90] [133]
# Pre-requis local : make build-ui (frontend/dist a jour)
set -euo pipefail
HOST="${1:-root@192.168.10.90}"
CT="${2:-133}"
tar -czf /tmp/infraos-ui.tgz -C frontend dist
scp -o StrictHostKeyChecking=no /tmp/infraos-ui.tgz "$HOST:/tmp/infraos-ui.tgz"
ssh -o StrictHostKeyChecking=no "$HOST" \
  "pct push $CT /tmp/infraos-ui.tgz /tmp/infraos-ui.tgz && pct exec $CT -- bash -c 'rm -rf /tmp/dist /usr/share/infraos/ui/* && tar --no-same-owner -xzf /tmp/infraos-ui.tgz -C /tmp && cp -r /tmp/dist/* /usr/share/infraos/ui/ && ls /usr/share/infraos/ui/assets && echo UI_OK'"
