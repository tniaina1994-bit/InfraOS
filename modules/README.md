# Catalogue des modules InfraOS (point 8)

Architecture prête pour les 17 modules. **État réel** (paquet/service) dès v1 ;
actions métier marquées `planned` (phase ultérieure, jamais d'échec silencieux).

| Module | Manifeste | Backend | Services Debian | État v1 |
|--------|-----------|---------|-----------------|---------|
| Identity Manager | `identity` | `modules/identity.py` | — (DB) | actif |
| Domain Manager | `domain` | `modules/domain.py` | samba-ad-dc | état |
| DNS Manager | `dns` | `modules/dns.py` | named | état |
| DHCP Manager | `dhcp` | `modules/dhcp.py` | kea-dhcp4-server | état |
| Network Manager | `network` | `modules/network.py` | iproute2/nft | actif |
| Firewall Manager | `firewall` | `modules/firewall.py` | nftables | état + ruleset |
| VPN Manager | `vpn` | `modules/vpn.py` | wireguard | état (ifaces wg) |
| IPAM | `ipam` | `modules/ipam.py` | — | planned |
| Network Discovery | `discovery` | `modules/discovery.py` | nmap | état |
| Monitoring | `monitoring` | `modules/monitoring.py` | node-exporter | état |
| File Server | `fileshare` | `modules/fileserver.py` | smbd | état |
| Backup Manager | `backup` | `modules/backup.py` | restic/borg | état outils |
| Security Center | `security` | `modules/security.py` | fail2ban | état |
| Log Analyzer | `loganalyzer` | `modules/loganalyzer.py` | journald | tail réel |
| Virtualization Manager | `virtualization` | `modules/virtualization.py` | libvirtd | état (dégradé LXC) |
| Update Manager | `updates` | `modules/updates.py` | apt | pending réel |
| Certificate Manager | `certificates` | `modules/certificates.py` | openssl | inventaire réel |
| (+ System, Logs génériques) | `system`, `logs` | `modules/system.py`, — | natif | actif |

# Phases : 1) identity, network, system 2) dns, dhcp, firewall, vpn
# 3) fileshare, domain, ipam, discovery 4) monitoring, backup, logs, updates
# 5) security, certificates, virtualization, loganalyzer
