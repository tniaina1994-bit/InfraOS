# Firewall nftables — abstraction FirewallRule, jamais de shell

- Modèle : chain (input/forward/output/prerouting/postrouting), action
  (accept/drop/dnat/masquerade/log), proto, src/dst CIDR, dport, in/out_if,
  nat_to, log, position, enabled — validé strictement (CIDR, ports, cohérence
  dnat→prerouting, masquerade→postrouting, dport→tcp/udp)
- Rendu : `table inet filter` (policies input/forward paramétrables) +
  `table ip nat` (prerouting dnat / postrouting masquerade)
- Sécurité : `nft -c -f` avant `nft -f` (argv figés, aucun shell), admin,
  audité. En LXC non-privilégié l'apply échoue proprement (dégradé :
  règles hôtes via Proxmox ; full sur ISO bare-metal/VM)
- API : CRUD `/firewall/rules`, `GET /preview`, `POST /apply`
