# VPN WireGuard (OpenVPN prévu, non implémenté)

- Serveurs `wgN` (address CIDR, port), clés générées côté serveur
  (`wg genkey`, privées 0600, jamais loggées), peers (pubkey, allowed_ips,
  endpoint host:port, keepalive)
- Rendu `/etc/wireguard/wgN.conf` (0600) + `restart wg-quick@wgN`
  (service validé contre la DB, admin, audité)
- Statut : `wg show <iface> dump` (up, nb peers) ; logs : journald
- API : CRUD serveurs/peers, `POST /servers/{id}/apply`
