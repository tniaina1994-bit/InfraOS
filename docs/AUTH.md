# Authentification InfraOS

## Phase 1 — locale (active)
- Comptes en DB (`users`, hash PBKDF2-SHA256, rôles `admin|operator|viewer`)
- Groupes (`groups` + `user_groups`) : rôle effectif = max(rôle user, rôles groupes),
  permissions dérivées (`GET /users/me/permissions`)
- `POST /api/v1/auth/login` → JWT HS256 + `jti`, session persistée (`sessions`)
- Sessions révocables : `POST /auth/logout`, `GET /auth/sessions`, `DELETE /auth/sessions/{id}`.
  Token au `jti` inconnu/révoqué = 401 (politique stricte)
- Politique mdp : 12 chars + chiffre (`INFRAOS_PASSWORD_MIN_LENGTH`,
  `INFRAOS_PASSWORD_REQUIRE_DIGIT`), appliquée création + changement
  (`POST /users/me/password`, révoque les autres sessions)
- Groupes : `GET/POST /groups`, `POST /groups/{n}/members`, `DELETE` membre
- Utilisateurs : `POST /users` (admin), `POST /users/{u}/{disable,enable}` (admin, pas d'auto-désactivation)
- Seed : `INFRAOS_ADMIN_PASSWORD` au premier démarrage (sinon `change-me` à changer)
- UI : page `/login`, token en localStorage, header `Authorization: Bearer`

## Phase 2 — prévue (stubs `backend/app/core/infraos/auth_providers.py`)
| Source | Config requise | Brique Debian |
|--------|---------------|---------------|
| LDAP | `INFRAOS_LDAP_URL` + `INFRAOS_LDAP_BASE_DN` | sssd / python-ldap |
| AD Samba | `INFRAOS_AD_DOMAIN` | Samba + Winbind (module `domain`) |
| Kerberos | `INFRAOS_KERBEROS_REALM` | krb5-user, kinit |

`GET /api/v1/auth/providers` expose l'état (`active|planned`).
`POST /login {"source":"ldap"}` renvoie `501` documenté tant que non configuré.
