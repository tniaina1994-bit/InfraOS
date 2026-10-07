# Découverte réseau — scans explicites admin (nmap/ARP)

- Lancement **manuel uniquement** (`POST /discovery/scans`, admin) : profils
  `ping` (-sn), `fast` (-F), `os` (-O). Cibles : CIDR ≥ /16 ou IP (0.0.0.0/0
  et /8 refusés). Sortie XML parsée (stdlib), jamais de shell.
- Stockage : `discovery_scans` + `discovery_hosts` (ip/mac/hostname/ports/os) ;
  comparaison `GET /compare?a=&b=` (new/gone/changed) ; ARP live `/arp`.
- Techs : nmap, ARP (/proc), ICMP/TCP via nmap. Scapy/SNMP : prévus si besoin.
