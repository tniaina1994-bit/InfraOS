# IPAM — réseaux, hôtes, allocation, liens

- `ipam_networks` (cidr, gateway auto-réservée, vlan), `ipam_hosts`
  (ip, mac, hostname, kind: static/reserved/dhcp/gateway)
- Allocation : première IP libre (saute réseau/broadcast/gateway/existants),
  `usage()` (total/utilisé/libre + inventaire)
- Liens (phase suivante) : DNS records (`POST /dns/...` depuis IPAM) et
  réservations DHCP (`POST /dhcp/...`) — endpoints prêts, câblage UI à venir
- Exemple : Network `192.168.20.0/24`, gateway `.254`, Devices `.10/.20/.50`
- API : CRUD networks/hosts, `GET /networks/{id}` (usage + inventaire)
