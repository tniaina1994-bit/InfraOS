#!/bin/bash
# Cree le LXC dev InfraOS aux specs officielles (idempotent si VMID existe).
# Spec: hostname infraos-dev, Debian 13 Trixie, non-privilégie, 4vCPU/8Go/2Go swap/40Go, vmbr0 dhcp, nesting=1
# Sans Docker: aucune dependance Docker, 100% natif systemd+pip.
# Usage: bash scripts/create-lxc.sh [root@192.168.10.90] [133]
set -euo pipefail
HOST="${1:-root@192.168.10.90}"
VMID="${2:-133}"
TEMPLATE="local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst"
echo "Templates dispo :"
ssh -o StrictHostKeyChecking=no "$HOST" "ls /var/lib/vz/template/cache/ | grep -i debian-13 || true"
if ssh -o StrictHostKeyChecking=no "$HOST" "pct status $VMID 2>/dev/null"; then
  echo "CT $VMID existe deja :"
  ssh -o StrictHostKeyChecking=no "$HOST" "pct config $VMID; pct status $VMID"
  exit 0
fi
echo "Creation CT $VMID infraos-dev (spec officielle)..."
ssh -o StrictHostKeyChecking=no "$HOST" bash -s -- "$VMID" "$TEMPLATE" <<'REMOTE'
set -e
VMID="$1"; TPL="$2"
pct create "$VMID" "$TPL" --hostname infraos-dev --cores 4 --memory 8192 --swap 2048 \
  --rootfs local-lvm:40 --net0 name=eth0,bridge=vmbr0,ip=dhcp --features nesting=1 \
  --unprivileged 1 --onboot 0 --ostype debian \
  --nameserver '192.168.10.252 8.8.8.8 1.1.1.1' --searchdomain Asareo.local \
  --password 'InfraOS-Dev-2026!'
pct start "$VMID"
sleep 5
pct exec "$VMID" -- bash -c 'cat /etc/os-release | head -n 3; hostname; which docker || echo NO_DOCKER_OK'
REMOTE
echo "CT $VMID infraos-dev OK. Provision: LXC_ID=$VMID make provision"
