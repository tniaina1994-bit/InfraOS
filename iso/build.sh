#!/bin/bash
# Build ISO InfraOS reproductible - A LANCER SUR BUILDER Debian 13 DEDIE (VM, pas le LXC).
# Ne transforme jamais le LXC en ISO : reconstruit depuis zero via live-build.
set -euo pipefail
OUTDIR="$(pwd)/build"
mkdir -p "$OUTDIR"
echo "==> [InfraOS ISO] builder check"
cat /etc/os-release | head -n 2
which lb || { echo "Installez live-build: apt-get install -y live-build"; exit 1; }

LB_DIR="$OUTDIR/lb"
rm -rf "$LB_DIR"; mkdir -p "$LB_DIR"
cd "$LB_DIR"
lb config \
  --distribution trixie \
  --archive-areas "main contrib non-free non-free-firmware" \
  --debian-installer live \
  --debian-installer-distribution trixie \
  --iso-application "InfraOS" \
  --iso-volume "InfraOS 13" \
  --image-name "infraos-13-amd64" \
  --bootloaders "syslinux grub-efi" \
  --architectures amd64

# Paquets InfraOS (base serveur infra) — depuis iso/packages.list
cp "$(pwd)/../packages.list" config/package-lists/infraos.list.chroot
# Overlay config InfraOS
if [ -d ../config ]; then
  cp -r ../config/* config/ 2>/dev/null || true
fi

echo "==> lb build (long)..."
lb build
ls -lh ./*.iso
sha256sum ./*.iso > SHA256SUMS
echo "ISO OK. Testez en VM Proxmox : SeaBIOS ou OVMF, 4Go RAM, boot ISO."
