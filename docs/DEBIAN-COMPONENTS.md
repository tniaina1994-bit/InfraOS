# Composants Debian réutilisés — rien de réimplémenté

| Besoin | Paquet Debian 13 | Piloté par | Manifest |
|--------|------------------|------------|----------|
| DNS | bind9 | templates + `systemctl is-active named` | modules/dns |
| DHCP | kea-dhcp4-server | config Kea JSON + service | modules/dhcp |
| Firewall | nftables | règles nft + service | modules/firewall |
| VPN | wireguard | wg-quick + clés | modules/vpn |
| Domaine | samba, winbind, krb5-user | samba-ad-dc | modules/domain |
| Fichiers | samba (smbd) | shares + ACL | modules/fileshare |
| Backup | restic, borgbackup | planifications | modules/backup |
| Updates | apt, unattended-upgrades | `updates.py` (APT natif) | modules/updates |
| Logs | systemd-journald + fichiers | `logging_conf.py` + audit | modules/logs |
| Monitoring | prometheus-node-exporter | scrape | modules/monitoring |
| Web | nginx | reverse proxy /api | ops/nginx-infraos.conf |
| IPAM/découverte | nmap, iproute2, sqlite | inventaire local | modules/ipam |

Règle : un nouveau besoin = d'abord chercher le paquet Debian existant,
le déclarer dans `packages:`, le piloter — jamais de protocole maison.
