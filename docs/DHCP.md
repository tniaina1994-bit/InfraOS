# DHCP Kea — scopes, réservations, baux, apply

- Source : tables `dhcp_scopes` / `dhcp_reservations`
- Rendu : `/etc/kea/kea-dhcp4.conf` (JSON Kea : subnet4, pools, option-data
  routers/DNS/domain, reservations hw-address, lifetimes)
- Sécurité : `kea-dhcp4 -t` obligatoire avant `restart kea-dhcp4-server`
  (allow-list, admin, audité)
- Baux : lecture memfile `/var/lib/kea/kea-leases4.csv` (tolérant si absent)
- API : CRUD scopes/réservations, `GET /leases`, `POST /apply`
