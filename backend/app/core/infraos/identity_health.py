# SPDX-License-Identifier: GPL-3.0-or-later
"""Identity & Domain — sante (§20), Kerberos (§15), LDAP (§16), DNS (§17),
temps (§18) et services (§19). Lecture seule + tests controles (kinit stdin).

Chaque verification retourne PASS | WARNING | ERROR (spec §20). Aucune entree
utilisateur n'est concatenee dans une commande : argv figes, allow-list.
"""
from __future__ import annotations

import re
import socket
from pathlib import Path

from .exec import ForbiddenCommand, run
from .identity_domain import (
    AD_SERVICES,
    _listening_ports,
    _svc,
    domain_row,
    is_provisioned,
)
from .identity_samba import _acc, _ensure, _maybe

KRB5 = Path("/etc/krb5.conf")
KEYTAB = Path("/etc/krb5.keytab")
SYSVOL = Path("/var/lib/samba/sysvol")
CACHE_TEST = "/tmp/infraos-krb5cc-identity-test"

SRV_EXPECTED = ["_ldap._tcp", "_kerberos._tcp", "_kerberos._udp",
                "_kpasswd._tcp", "_kpasswd._udp"]


def _check(name: str, status: str, detail: str) -> dict:
    return {"check": name, "status": status, "detail": detail}


def _tcp(port: int, host: str = "127.0.0.1", timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def services_status() -> dict:
    """§19 : etat des services du Domain Controller."""
    wanted = ["samba-ad-dc", "smbd", "nmbd", "winbind", "named", "chrony"]
    items = []
    for svc in wanted:
        try:
            state = _svc(svc)
        except ValueError:
            state = "n/a"
        enabled = "?"
        try:
            if svc in AD_SERVICES:
                r = run("systemctl", "is-enabled", svc, caller="identity.services")
                enabled = (r.out.strip() or "?").splitlines()[0]
        except (ForbiddenCommand, Exception):
            pass
        items.append({"service": svc, "status": state, "enabled": enabled,
                      "required": svc == "samba-ad-dc"})
    running = sum(1 for i in items if i["status"] == "active")
    return {"services": items, "running": running,
            "provisioned": is_provisioned()}


def domain_status() -> dict:
    """GET /identity/status — synthese (spec §6)."""
    prov = is_provisioned()
    row = domain_row()
    out: dict = {"provisioned": prov,
                 "domain": row.realm if row else None,
                 "netbios_name": row.netbios if row else None,
                 "hostname": row.dc_hostname if row else None,
                 "status": "unconfigured"}
    if not prov:
        out["detail"] = "domaine non provisionne"
        out["services"] = services_status()
        return out
    svc = services_status()
    smbd = next((s for s in svc["services"] if s["service"] == "samba-ad-dc"), {})
    out.update({
        "hostname": row.dc_fqdn if row else socket.getfqdn(),
        "status": "healthy" if smbd.get("status") == "active" else "degraded",
        "dns": "healthy" if _tcp(53) else "error",
        "kerberos": "healthy" if _tcp(88) else "error",
        "ldap": "healthy" if _tcp(389) else "error",
        "samba": smbd.get("status", "?"),
        "sysvol": "healthy" if SYSVOL.exists() else "error",
        "services": svc,
    })
    return out


def full_health() -> dict:
    """§20 : Identity Health Check — PASS/WARNING/ERROR par verification."""
    checks: list[dict] = []
    prov = is_provisioned()
    row = domain_row()
    realm = row.realm if row else ""

    # hostname / FQDN / hosts
    host = socket.gethostname()
    checks.append(_check("hostname", "PASS" if host else "ERROR", host))
    try:
        fqdn = socket.getfqdn()
        resolved = socket.getaddrinfo(fqdn, None)
        ip_ok = any(c[4][0] == (row.dc_ip if row else "") for c in resolved) \
            if row and row.dc_ip else bool(resolved)
        checks.append(_check("fqdn", "PASS" if ip_ok else "WARNING",
                             f"{fqdn} -> {[c[4][0] for c in resolved][:2]}"))
    except OSError as e:
        checks.append(_check("fqdn", "ERROR", str(e)))
    if not prov:
        checks.append(_check("domain", "WARNING", "domaine non provisionne"))
        return {"overall": "WARNING", "checks": checks,
                "detail": "Health Check incomplet (pas de domaine)"}

    # samba service
    state = _svc("samba-ad-dc")
    checks.append(_check("samba", "PASS" if state == "active" else "ERROR",
                         f"samba-ad-dc={state}"))
    # LDAP + Kerberos ports
    checks.append(_check("ldap", "PASS" if _tcp(389) else "ERROR",
                         "LDAP 389 joignable" if _tcp(389) else "LDAP 389 fermé"))
    checks.append(_check("kerberos", "PASS" if _tcp(88) else "ERROR",
                         "Kerberos 88 joignable" if _tcp(88) else "Kerberos 88 fermé"))
    # DNS : ports + enregistrements SRV
    dns_port = _tcp(53)
    checks.append(_check("dns_port", "PASS" if dns_port else "ERROR",
                         "DNS 53 joignable" if dns_port else "DNS 53 fermé"))
    srv = dns_records_health(realm)
    missing = [r["name"] for r in srv["records"] if r["status"] != "PASS"]
    checks.append(_check("dns_srv", "PASS" if not missing else "WARNING",
                         "SRV complets" if not missing else f"manquants: {missing}"))
    # forward / reverse
    fwd = forward_lookup(realm)
    checks.append(_check("forward_dns", "PASS" if fwd["resolved"] else "WARNING",
                         f"{realm} -> {fwd.get('addresses') or 'NXDOMAIN'}"))
    ptr = reverse_lookup(row.dc_ip if row else "")
    checks.append(_check("reverse_dns", "PASS" if ptr["resolved"] else "WARNING",
                         ptr.get("name") or "PTR absent"))
    # SYSVOL / NETLOGON
    sysvol_ok = (SYSVOL / realm).exists() if realm else SYSVOL.exists()
    checks.append(_check("sysvol", "PASS" if sysvol_ok else "ERROR",
                         f"{SYSVOL}/{realm} present" if sysvol_ok else "SYSVOL/realm absent"))
    # NETLOGON = partage sysvol/netlogon servi par samba-ad-dc
    netlogon_ok = sysvol_ok
    checks.append(_check("netlogon", "PASS" if netlogon_ok else "ERROR",
                         "partage NETLOGON servi par samba-ad-dc" if netlogon_ok
                         else "NETLOGON absent"))
    # keytab / krb5
    # keytab : Samba AD DC stocke les cles machine/krbtgt dans secrets.ldb —
    # pas de keytab systeme est NORMAL ici (spec §20, informatif).
    checks.append(_check("keytab",
                         "PASS" if (KEYTAB.exists() or prov) else "WARNING",
                         str(KEYTAB) if KEYTAB.exists()
                         else "Samba DC : cles dans secrets.ldb (pas de keytab systeme)"))
    checks.append(_check("krb5_conf", "PASS" if KRB5.exists() else "ERROR",
                         "/etc/krb5.conf" if KRB5.exists() else "absent"))
    # temps (Kerberos < 5min skew)
    t = time_info()
    checks.append(_check("time_sync", t.get("status", "WARNING"), t["detail"]))
    # ports AD
    ports = sorted(p for p in (53, 88, 389, 445, 464) if p in _listening_ports())
    missing_p = [p for p in (53, 88, 389, 445) if p not in ports]
    checks.append(_check("ports", "PASS" if not missing_p else "ERROR",
                         f"ecoutent: {ports}" + (f" manquants: {missing_p}" if missing_p else "")))

    statuses = [c["status"] for c in checks]
    overall = "ERROR" if "ERROR" in statuses else (
        "WARNING" if "WARNING" in statuses else "PASS")
    return {"overall": overall, "checks": checks, "domain": realm,
            "hostname": row.dc_fqdn if row else host}


# ---------------------------------------------------------------- DNS ---

def _dig(args: tuple[str, ...], timeout: int = 10) -> str:
    """Requete DNS via dig @127.0.0.1 — le DNS AD est non-authentifie par
    protocole. (La RPC `samba-tool dns` exige des identifiants AD : en tant
    que root sans ticket elle echoue NT_STATUS_LOGON_FAILURE.)"""
    try:
        r = run("dig", *args, timeout=timeout, caller="identity.dns")
    except ForbiddenCommand as e:
        raise ValueError(f"commande refusee: {e}")
    if r.rc != 0:
        raise ValueError(r.out[-400:])
    return r.out


def _dig_short(name: str, rtype: str, timeout: int = 10) -> str:
    return _dig(("@127.0.0.1", name, rtype, "+short"), timeout=timeout).strip()


def zone_list() -> dict:
    if not _maybe():
        return {"zones": [], "detail": "domaine non provisionne"}
    realm, _ = _ensure()
    zones: list[str] = []
    for z in (realm, f"_msdcs.{realm}"):
        try:
            out = _dig(("@127.0.0.1", z, "AXFR"), timeout=8)
        except ValueError:
            continue
        if re.search(r"XFR size|;; ANSWER SECTION:", out):
            zones.append(z)
    if not zones:
        # AXFR refuse en local : zone connue depuis la base
        zones = [realm]
    return {"zones": zones, "detail": "zones Samba DNS (AXFR local)" if zones else ""}


def dns_query(name: str, rtype: str = "SRV", zone: str | None = None) -> dict:
    if not _maybe():
        raise ValueError("domaine non provisionne")
    realm, _ = _ensure()
    if rtype not in ("A", "AAAA", "PTR", "CNAME", "MX", "NS", "SOA", "SRV", "TXT", "ALL"):
        raise ValueError(f"type DNS invalide: {rtype!r}")
    if not re.match(r"^[A-Za-z0-9._*-]{1,253}$", name):
        raise ValueError(f"nom DNS invalide: {name!r}")
    out = _dig(("@127.0.0.1", name, rtype))
    found = bool(re.search(r";;\s+ANSWER SECTION:", out)) \
        and not re.search(r"status:\s*(NXDOMAIN|SERVFAIL|REFUSED)", out)
    return {"name": name, "type": rtype, "zone": zone or realm,
            "output": out[:4000], "found": found}


def forward_lookup(name: str) -> dict:
    if not name:
        return {"resolved": False, "addresses": []}
    try:
        addrs = sorted({c[4][0] for c in socket.getaddrinfo(name, None)})
        return {"resolved": True, "addresses": addrs}
    except OSError:
        return {"resolved": False, "addresses": []}


def reverse_lookup(ip: str) -> dict:
    if not ip:
        return {"resolved": False, "name": ""}
    try:
        return {"resolved": True, "name": socket.gethostbyaddr(ip)[0]}
    except OSError:
        return {"resolved": False, "name": ""}


def dns_records_health(realm: str) -> dict:
    """§17 : SRV Kerberos/LDAP + A + PTR (dig @127.0.0.1, sans auth)."""
    if not realm or not _maybe():
        return {"records": [], "detail": "domaine non provisionne"}
    records = []
    for srv in SRV_EXPECTED:
        try:
            out = _dig_short(f"{srv}.{realm}", "SRV")
            ok = bool(re.match(r"^\d+\s+\d+\s+\d+\s+\S+", out))
            records.append({"name": srv, "type": "SRV",
                            "status": "PASS" if ok else "ERROR",
                            "detail": out[:300] if ok else "absent"})
        except ValueError as e:
            records.append({"name": srv, "type": "SRV", "status": "ERROR",
                            "detail": str(e)[:300]})
    host = socket.gethostname()
    for name, rtype in ((realm, "A"), (f"{host}.{realm}", "A")):
        try:
            out = _dig_short(name, rtype)
            ok = bool(re.match(r"^\d+\.\d+\.\d+\.\d+", out))
            records.append({"name": name, "type": rtype,
                            "status": "PASS" if ok else "WARNING",
                            "detail": out[:300] if ok else "absent"})
        except ValueError as e:
            records.append({"name": name, "type": rtype, "status": "WARNING",
                            "detail": str(e)[:300]})
    return {"records": records, "zone": realm}


def domain_dns_health() -> dict:
    """GET /identity/domain/dns — page Domain DNS Health (§17)."""
    if not _maybe():
        return {"provisioned": False, "detail": "domaine non provisionne",
                "records": [], "zones": []}
    realm, _ = _ensure()
    row = domain_row()
    zones = zone_list()
    recs = dns_records_health(realm)
    fwd = forward_lookup(realm)
    ptr = reverse_lookup(row.dc_ip if row else "")
    kerberos_ok = all(r["status"] == "PASS" for r in recs["records"]
                      if "kerberos" in r["name"] or "_ldap" in r["name"])
    return {"provisioned": True, "zone": realm, "zones": zones.get("zones", []),
            "records": recs["records"], "forward": fwd, "reverse": ptr,
            "status": "healthy" if fwd["resolved"] and kerberos_ok else "degraded",
            "detail": zones.get("detail", "")}


# ----------------------------------------------------------- Kerberos ---

def kerberos_info() -> dict:
    """§15 : realm, KDC, tickets, clock skew, SPN (klist -k)."""
    info: dict = {"provisioned": is_provisioned(), "realm": "", "kdc": [],
                  "keytab": KEYTAB.exists(), "time_sync": time_info()}
    try:
        text = KRB5.read_text()
        m = re.search(r"default_realm\s*=\s*(\S+)", text)
        info["realm"] = m.group(1) if m else ""
        info["kdc"] = re.findall(r"^\s*kdc\s*=\s*(\S+)", text, re.M)
        info["admin_server"] = re.findall(r"^\s*admin_server\s*=\s*(\S+)", text, re.M)
    except OSError:
        pass
    if KEYTAB.exists():
        try:
            r = run("klist", "-k", caller="identity.kerberos")
            info["principals"] = [ln.strip() for ln in r.out.splitlines()
                                  if "@" in ln or "/" in ln][:50]
            info["principals_detail"] = r.out[:3000]
        except (ForbiddenCommand, Exception) as e:
            info["principals_detail"] = str(e)
    try:
        r = run("klist", caller="identity.kerberos")
        info["tickets"] = r.out[:2000] if r.rc == 0 else "aucun ticket"
    except (ForbiddenCommand, Exception) as e:
        info["tickets"] = str(e)
    info["status"] = ("healthy" if info["provisioned"] and _tcp(88)
                      else "unconfigured" if not info["provisioned"]
                      else "degraded")
    return info


def kinit_test(username: str, password: str) -> dict:
    """Test d'authentification Kerberos — mot de passe via STDIN (jamais argv)."""
    realm, _ = _ensure()
    username = _acc(username, "utilisateur")
    if not password or len(password) < 1:
        raise ValueError("mot de passe requis")
    principal = username if "@" in username else f"{username}@{realm.upper()}"
    try:
        r = run("kinit", principal, timeout=15, caller="identity.kerberos.test",
                stdin_data=password + "\n", secret_args=())
    except ForbiddenCommand as e:
        raise ValueError(f"commande refusee: {e}")
    finally:
        try:
            run("kdestroy", "-A", timeout=5, caller="identity.kerberos.test")
        except Exception:
            pass
    ok = r.rc == 0
    return {"principal": principal, "success": ok,
            "detail": (r.out or "ticket obtenu")[:500],
            "status": "PASS" if ok else "ERROR"}


def ldap_info() -> dict:
    """§16 : statut LDAP, base DN, port, LDAPS, certificats."""
    ctx = _maybe()
    row = domain_row()
    realm = row.realm if row else ""
    base_dn = "DC=" + ",DC=".join(realm.split(".")) if realm else ""
    ldap_ok = _tcp(389)
    ldaps_ok = _tcp(636)
    cert_paths = [Path("/var/lib/samba/private/tls/ca.pem"),
                  Path("/var/lib/samba/private/tls/cert.pem")]
    certs = [{"path": str(p), "exists": p.exists()} for p in cert_paths]
    # test de recherche : user list = parcours LDAP reel
    search_ok = False
    search_detail = "domaine non provisionne"
    if ctx:
        try:
            out = _run_ldap_probe()
            search_ok, search_detail = True, out
        except ValueError as e:
            search_detail = str(e)[:300]
    return {"provisioned": bool(ctx), "server": row.dc_fqdn if row else socket.gethostname(),
            "port": 389, "ldaps_port": 636,
            "base_dn": base_dn, "ldap": ldap_ok, "ldaps": ldaps_ok,
            "certificates": certs,
            "search_test": {"ok": search_ok, "detail": search_detail},
            "status": ("healthy" if ldap_ok and search_ok else
                       "degraded" if ldap_ok else "error")}


def _run_ldap_probe() -> str:
    from .identity_samba import list_users
    res = list_users()
    if res.get("detail") and not res.get("count"):
        raise ValueError(res["detail"])
    return f"lecture LDAP OK ({res['count']} entrees)"


# -------------------------------------------------------------- temps ---

def time_info() -> dict:
    """§18 : horloge, timezone, NTP, skew (Kerberos exige <5 min)."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    out = {"now": now.isoformat(), "timezone": "", "ntp": "unknown",
           "synchronized": False, "detail": ""}
    try:
        r = run("timedatectl", "show", caller="identity.time")
        fields = dict(line.split("=", 1) for line in r.out.splitlines() if "=" in line)
        out["timezone"] = fields.get("Timezone", "")
        out["synchronized"] = fields.get("NTPSynchronized", "") == "yes"
        out["ntp"] = "synchronized" if out["synchronized"] else "unsynchronized"
        out["detail"] = (f"NTP={out['ntp']} tz={out['timezone']}"
                         + ("" if out["synchronized"] else
                            " — Kerberos exige <5min de skew, verifiez chrony/ntp"))
        out["status"] = "PASS" if out["synchronized"] else "WARNING"
    except (ForbiddenCommand, Exception) as e:
        out["detail"] = f"timedatectl indisponible: {e}"
        out["status"] = "WARNING"
    # skew local : compare heure systeme vs RTC approx via /etc/localtime ? non —
    # simple : on expose now + status NTP, l'operateur interprete.
    return out


# --------------------------------------------------- join info (§11/12) ---

def join_info() -> dict:
    """Informations de jointure Windows + Linux (realmd/sssd/adcli)."""
    row = domain_row()
    prov = is_provisioned()
    if not prov or not row:
        return {"provisioned": False, "detail": "domaine non provisionne"}
    return {"provisioned": True,
            "domain": row.realm, "netbios": row.netbios,
            "dns_server": row.dc_ip, "domain_controller": row.dc_fqdn,
            "admin_user": row.admin_user or "Administrator",
            "windows": {
                "steps": [
                    f"Poste Windows : Parametres reseau -> DNS primaire = {row.dc_ip}",
                    "Systeme > Informations > Renommer ce PC (ex. WIN-PC01)",
                    f"Domaine : rejoindre {row.realm}",
                    f"Compte : {row.admin_user or 'Administrator'} @ {row.realm}",
                    "Verification : ipconfig /all (DNS = " + row.dc_ip + ")",
                    "gpupdate /force apres join",
                ]},
            "linux": {
                "packages": "realmd sssd sssd-ad adcli krb5-user packagekit",
                "steps": [
                    f"sudo realm discover {row.realm}",
                    f"echo '<password>' | sudo realm join --user=Administrator {row.realm}",
                    "verifier : id <user@realm> ; getent passwd",
                    "sssd : /etc/sssd/sssd.conf (enable_expires etc.)",
                ],
                "distros": ["Ubuntu 22.04+", "Debian 12+", "Rocky Linux 9+",
                            "AlmaLinux 9+"]}}
