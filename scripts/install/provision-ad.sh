#!/bin/bash
# Provision Samba AD DC — A LANCER EN CLI SUR HOTE ISO (bare-metal/VM), JAMAIS en LXC ni depuis le Web.
# Usage: bash scripts/provision-ad.sh AD.EXAMPLE.LOCAL ADMINPASS
# Pre-requis: Debian 13, paquets samba smbclient winbind krb5-user, ports AD libres, DNS resolvant le domaine.
set -euo pipefail
DOMAIN="${1:?usage: $0 DOMAINE.TLD MOTDEPASSE_ADMIN}"
ADMINPW="${2:?usage: $0 DOMAINE.TLD MOTDEPASSE_ADMIN}"
REALM=$(echo "$DOMAIN" | tr 'a-z' 'A-Z')
if systemd-detect-virt 2>/dev/null | grep -q lxc; then
  echo "REFUSE: provision AD en LXC non supporte (utilisez l'ISO sur VM/bare-metal)."
  echo "Lisez GET /api/v1/domain/readiness pour le detail."
  exit 1
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq samba smbclient winbind krb5-user
[ -f /etc/samba/smb.conf ] && mv /etc/samba/smb.conf /etc/samba/smb.conf.bak.$(date +%s)
samba-tool domain provision --realm="$REALM" --domain="${DOMAIN%%.*}" \
  --server-role=dc --dns-backend=SAMBA_INTERNAL --adminpass="$ADMINPW"
systemctl unmask samba-ad-dc
systemctl enable --now samba-ad-dc
systemctl disable --now smbd nmbd winbind 2>/dev/null || true
echo "AD provisionne: realm=$REALM. Test: samba-tool user list ; kinit administrator"
