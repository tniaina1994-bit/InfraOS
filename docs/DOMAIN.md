# Domaine Windows/Linux — stratégie Samba AD (pas de réimplémentation)

> **Implémentation complète** : voir **[IDENTITY.md](IDENTITY.md)** —
> module `identity`, API `/api/v1/identity/*`, UI « Annuaire & partage »,
> provision Samba AD DC guidée (preflight → setup → health), utilisateurs,
> groupes, OU, ordinateurs, politiques, jointure, audit.

## Principe
InfraOS ne réimplémente **ni** Active Directory, **ni** Kerberos, **ni** LDAP.
Le contrôleur de domaine = **Samba AD DC** (Debian natif), avec Kerberos
(`krb5-user`) et LDAP intégrés. InfraOS pilote : provision (CLI), état
(API lecture), jointure documentée.

## Pourquoi pas en LXC dev
`GET /api/v1/domain/readiness` répond `warn` en LXC : ports privilégiés,
persistance du `sam.ldb`, DNS du domaine. Provisionnez sur **ISO
bare-metal/VM** via `scripts/install/provision-ad.sh` (refuse le LXC).

## Intégrations futures (stubs `auth_providers.py`)
- **LDAP** : `INFRAOS_LDAP_URL` + `INFRAOS_LDAP_BASE_DN` (sssd/python-ldap)
- **AD** : `INFRAOS_AD_DOMAIN` (jointure `realm join`, Winbind/sssd)
- **Kerberos** : `INFRAOS_KERBEROS_REALM` (`kinit`, keytab service)

## Identity locale (phase 1, active)
users/groups/roles en DB : rôles `admin|operator|viewer`, rôle effectif =
max(rôle user, rôles groupes), permissions dérivées (`GET /users/me/permissions`),
politique mdp (12 chars + chiffre), sessions JWT révocables, audit complet.
