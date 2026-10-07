# Protocole InfraOS Agent (Linux + Windows — phase ultérieure)

L'agent est un binaire/service léger qui pousse ses métriques au Core.

1. Enregistrement (admin, une fois) : `POST /api/v1/monitoring/agents`
   `{"hostname":"pc1","os":"windows","token":"<32+ chars>"}`.
2. Push périodique (60s, sans JWT) : `POST /api/v1/monitoring/agents/push`
   `{"hostname":"pc1","token":"...","metrics":{"cpu":12,"mem":44,"disk":60,
   "load1":"0.5","net_rx":1,"net_tx":2,"uptime":3600,"temp":""}}`.
3. Lecture : `GET /monitoring/history?host=pc1`, `GET /monitoring/agents`
   (last_seen). Windows : même JSON (Go ou Python embarqué).
