# installer/ — units systemd + nginx (+ TLS prêt)

- `systemd/infraos-api.service` : uvicorn via `/opt/infraos/venv`
  (créé par `scripts/install/bootstrap.sh`), cwd `/opt/infraos/backend/app`.
- `nginx-infraos.conf` : UI + proxy `/api/`, docs OpenAPI, bloc 443 commenté
  (TLS : Certbot ou module certificates, puis HSTS).
