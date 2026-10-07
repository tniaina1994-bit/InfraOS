# InfraOS Agent — architecture

```
InfraOS Server (API FastAPI, Postgres)
      │ HTTPS / API sécurisée (token agent, pas de JWT user)
      ▼
InfraOS Agent (léger, push 60s)
      ├── Linux (systemd)
      └── Windows (tâche planifiée / service)
```

## Protocole (docs/AGENT.md)
1. Enregistrement (admin, une fois) : `POST /api/v1/monitoring/agents`
   `{"hostname","os":"linux|windows","token":"32+ chars"}`.
2. Push : `POST /api/v1/monitoring/agents/push`
   `{"hostname","token","metrics":{cpu,mem,disk,load1,net_rx,net_tx,uptime,temp}}`.
3. L'agent ne reçoit JAMAIS d'ordre (push-only v1) ; pas d'écoute réseau côté agent.

## Remontées
CPU, RAM, disque, processus (top 5), services (liste blanche), réseau
(rx/tx), OS (platform), événements (démarrage/arrêt agent).

## Référence
`agent/infraos_agent.py` — stdlib + psutil uniquement (Linux + Windows),
config `agent/agent.yaml`, service `agent/infraos-agent.service`,
tâche Windows `agent/windows-task.xml`. Token en 0600, jamais loggé.
