# Sécurité InfraOS (dès la conception)

1. **Aucune commande shell arbitraire depuis le Web.** L'UI appelle l'API (REST),
   l'API appelle `backend/app/core/infraos/exec.py::run()` qui n'autorise qu'une allow-list
   fermée (`systemctl is-active/is-enabled/status/start/stop/restart/enable/disable`,
   `systemd-detect-virt`, `ip addr/route/link`, `apt list` + `apt-get check/install`,
   `dpkg-query -W`, `dpkg -l`, `journalctl --no-pager`, `nft list`),
   avec `shell=False`, refus des métacaractères (`; & | \` $`) et timeout. Tout le reste lève
   `ForbiddenCommand`. Les **mutations** (systemctl start/stop/..., apt install)
   exigent en plus : nom validé contre une liste fermée (jamais d'entrée brute),
   RBAC **admin**, audit + événement.
2. **Audit.** Chaque `exec.run()` et chaque requête API est appendée à
   `/var/log/infraos/audit.log` (0600) via `AuditMiddleware`.
3. **Config/secrets.** `/etc/infraos/config.yaml` en 0600, secret JWT 32+ chars
   via env `INFRAOS_JWT_SECRET` en prod. Aucun mot de passe en clair dans le code.
4. **Réseau.** API écoute `127.0.0.1` en prod derrière nginx (TLS) ; `0.0.0.0`
   uniquement en LXC dev. Firewall deny-by-default sur ISO.
5. **Mises à jour.** APT natif ; l'API v1 est lecture seule (`check_updates`),
   aucun upgrade aveugle déclenché depuis le Web.
7. **Défense API.** Rate-limit login (5/min/IP, 429, `INFRAOS_RATE_LOGIN_N`),
   headers (`X-Frame-Options: DENY`, `nosniff`, CSP), CORS restrictif
   (`INFRAOS_CORS_ORIGINS`, méthodes GET/POST/PUT/DELETE, plus de `*`),
   validation Pydantic + validateurs métier, audit+événement par requête.
8. **CSRF.** Non applicable : JWT en `Authorization: Bearer` (localStorage),
   pas de cookie de session → aucune route ne dépend de l'ambient authority.
9. **HTTPS.** Terminé par nginx (config `ops/nginx-infraos.conf`, bloc 443 +
   chemins cert commentés, HSTS à activer avec le cert) ; API en 127.0.0.1
   derrière le proxy en prod.
10. **Secrets.** `/etc/infraos/secrets/` 0700/fichiers 0600, jamais en DB ni
    en log (`:***@`), JWT 32+ chars via env.
11. **Moindre privilège.** Service systemd root en dev (requis : nft, systemctl,
    bind/kea) compensé par allow-list + RBAC + audit ; travaux futurs :
    capabilities (`CAP_NET_ADMIN`) et utilisateur dédié + sudoers ciblé.
12. **Rôles.** `superadmin > admin > operator > readonly(viewer)` en DB
    (tables roles/permissions/user_roles, seed idempotent) ; on ne peut
    attribuer un rang ≥ au sien ; auto-révocation interdite.
13. **Vérif continue.** `make security-check` = `no-arbitrary-shell.sh`
    (grep `shell=True`, `os.system`, `eval(`, `subprocess` hors fichiers
    autorisés) + `no-microservice.sh` + `no-docker-check.sh`.

Si tu ajoutes un module : déclare `packages:` Debian dans le manifest,
passe par `exec.run()`, ajoute un test dans `backend/tests/test_exec.py`.
