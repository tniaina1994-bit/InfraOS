# Réseau — stratégie cohérente et documentée

## Choix
| Besoin | Outil | Écriture |
|--------|-------|----------|
| Lecture interfaces/IP/routes | `ip addr/route/link` (iproute2, toujours présent) | — |
| Persistance | systemd-networkd drop-ins `10-infraos-*` | API stage |
| Application | `networkctl reload` (doux) | `confirm:true` |
| DNS resolver | `/etc/resolv.conf` (lecture) | via module DNS (BIND9) |
| VLAN | `.netdev` + `.network` | API stage + reload |
| Bridge/Bonding | `.netdev` (phase ultérieure) | CLI |

## Pourquoi systemd-networkd (pas NetworkManager, pas ifupdown)
- Déclaratif, versionnable, rollback (`.infraos-bak`), présent par défaut,
  pas de daemon supplémentaire. NetworkManager reste utilisable côté
  desktop mais n'est pas requis sur InfraOS serveur.

## Sécurité
- Jamais de `reconfigure` aveugle depuis le Web ; `confirm:true` exigé pour
  appliquer ; l'interface de la session courante est protégée
  (refus sans confirm) ; backup auto avant écrasement.
- En LXC : lecture OK, écriture persistée mais appliquée par l'hôte
  selon bridge Proxmox — documenté dégradé partiel.
