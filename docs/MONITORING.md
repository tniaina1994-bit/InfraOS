# Monitoring serveur + agent futur (docs/AGENT.md)

- Serveur : psutil (CPU/RAM/disque/réseau/charge/processus/uptime) +
  température si capteurs + services systemd via System Manager.
- `GET /current` (live), `POST /collect` (échantillon DB),
  `GET /history?host=&limit=` (courbes UI).
