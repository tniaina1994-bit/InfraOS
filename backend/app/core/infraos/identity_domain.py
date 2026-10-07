# SPDX-License-Identifier: GPL-3.0-or-later
"""Identity & Domain — provisioning Samba AD DC (couche metier, jamais de shell).

Philo (spec §37) : React -> FastAPI -> IdentityService -> SambaService -> Samba AD.
- validation stricte de chaque entree (regex + ipaddress) AVANT tout exec ;
- samba-tool via exec.run() allow-liste, argv fixe, shell=False ;
- mots de passe JAMAIS dans argv non masque (secret_args) ni en base ;
- /etc/hosts + /etc/krb5.conf ecrits par Python (blocs marques INFRAOS IDENTITY) ;
- audit file + events a chaque etape.
"""
from __future__ import annotations

import ipaddress
import re
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

from .exec import run
from .logging_conf import get_logger

log = get_logger("infraos.identity")

# --- validateurs (spec §22 : entrees validees avant toute execution) ---
REALM_RE = re.compile(
    r"^(?=.{4,253}$)[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?"
    r"(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$")
NETBIOS_RE = re.compile(r"^[A-Za-z0-9]{1,15}$")
HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")

SAMDB = Path("/var/lib/samba/private/sam.ldb")
SYSVOL = Path("/var/lib/samba/sysvol")
SECRET_DIR = Path("/etc/infraos/secrets")
HOSTS = Path("/etc/hosts")
KRB5 = Path("/etc/krb5.conf")
RESOLV = Path("/etc/resolv.conf")
MARK_B = "# --- BEGIN INFRAOS IDENTITY ---"
MARK_E = "# --- END INFRAOS IDENTITY ---"

AD_SERVICES = ("samba-ad-dc", "smbd", "nmbd", "winbind", "named", "chrony")


def validate_inputs(domain: str, netbios: str, hostname: str, ip: str) -> dict:
    """Valide domaine/NetBIOS/hostname/IP. Leve ValueError detaille."""
    domain = (domain or "").strip().lower()
    netbios = (netbios or "").strip().upper()
    hostname = (hostname or "").strip().lower().split(".")[0]
    ip = (ip or "").strip()
    if not REALM_RE.match(domain):
        raise ValueError(f"nom de domaine invalide: {domain!r} (ex: corp.example.internal)")
    if not NETBIOS_RE.match(netbios):
        raise ValueError(f"NetBIOS invalide: {netbios!r} (1-15 caracteres alphanumeriques)")
    if not HOST_RE.match(hostname):
        raise ValueError(f"hostname invalide: {hostname!r}")
    try:
        ipaddress.IPv4Address(ip)
    except ValueError:
        raise ValueError(f"IPv4 invalide: {ip!r}")
    return {"domain": domain, "netbios": netbios, "hostname": hostname, "ip": ip,
            "fqdn": f"{hostname}.{domain}"}


def is_provisioned() -> bool:
    return SAMDB.exists()


def ensure_secret_dir() -> Path:
    """§23 : /etc/infraos/secrets/ 0700 — aucun secret en clair en base."""
    SECRET_DIR.mkdir(parents=True, exist_ok=True)
    try:
        SECRET_DIR.chmod(0o700)
    except OSError:
        pass
    readme = SECRET_DIR / "README"
    if not readme.exists():
        readme.write_text(
            "InfraOS Secret Manager (concept)\n"
            "- aucun mot de passe / cle Kerberos / secret API en clair dans PostgreSQL ;\n"
            "- les mots de passe saisis dans l'UI (creation domaine, reset) ne sont\n"
            "  utilises que de facon transitoire (argv masque ou stdin) ;\n"
            "- ce repertoire (0700) est reserve aux futurs secrets d'integration.\n")
    return SECRET_DIR


def domain_row(realm: str | None = None):
    from .db import get_session
    from .models import IdentityDomain
    s = get_session()
    try:
        q = s.query(IdentityDomain)
        return (q.filter_by(realm=realm).first() if realm else q.order_by(IdentityDomain.id.desc()).first())
    finally:
        s.close()


def _hosts_block(v: dict) -> str:
    return (f"{MARK_B}\n{v['ip']}\t{v['fqdn']} {v['hostname']}\n{MARK_E}\n")


def write_hosts(v: dict) -> dict:
    """Ecrit/actualise le bloc INFRAOS IDENTITY de /etc/hosts (avec backup)."""
    try:
        text = HOSTS.read_text()
    except OSError:
        text = ""
    backup = None
    if text.strip():
        bak = Path(str(HOSTS) + ".infraos-bak")
        if not bak.exists():
            bak.write_text(text)
            backup = str(bak)
    if MARK_B in text and MARK_E in text:
        head, rest = text.split(MARK_B, 1)
        _, tail = rest.split(MARK_E, 1)
        text = head + _hosts_block(v) + tail.lstrip("\n")
    else:
        text = text.rstrip("\n") + "\n" + _hosts_block(v)
    # Neutralise les lignes conflictuelles (type PVE "127.0.1.1") : sans cela
    # le hostname brut resout en 127.0.1.1 AVANT notre bloc INFRAOS.
    cleaned = []
    for line in text.splitlines():
        if not line.startswith((MARK_B, MARK_E)) and re.match(r"^127\.0\.1\.1\b", line):
            toks = line.split()
            aliases = [a for a in toks[1:] if a not in (v["hostname"], v["fqdn"])]
            if aliases:
                line = toks[0] + "\t" + " ".join(aliases)
            else:
                continue
        cleaned.append(line)
    text = "\n".join(cleaned) + "\n"
    HOSTS.write_text(text)
    return {"file": str(HOSTS), "backup": backup, "entry": f"{v['ip']} {v['fqdn']}"}


def write_resolv(v: dict) -> dict:
    """Le DC devient son propre resolver (127.0.0.1) : sans cela le realm
    ne se resout pas (upstream = routeur, ignorant le domaine). Backup 1x."""
    try:
        old = RESOLV.read_text()
    except OSError:
        old = ""
    backup = None
    if old.strip():
        bak = Path(str(RESOLV) + ".infraos-bak")
        if not bak.exists():
            try:
                bak.write_text(old)
                backup = str(bak)
            except OSError:
                pass
    upstream = _resolv_forwarder()
    lines = ["# InfraOS Identity — le Domain Controller est son propre DNS",
             "nameserver 127.0.0.1",
             f"search {v['domain']}"]
    if upstream and upstream != "127.0.0.1":
        lines.append(f"# forwarder Samba (dns forwarder = {upstream})")
    try:
        RESOLV.write_text("\n".join(lines) + "\n")
    except OSError as e:
        raise ValueError(f"ecriture /etc/resolv.conf impossible: {e}")
    return {"file": str(RESOLV), "backup": backup,
            "nameserver": "127.0.0.1", "forwarder": upstream}


def write_krb5(v: dict, kdc: str | None = None) -> dict:
    """Ecrit /etc/krb5.conf pour le realm (bloc marque, backup si existant)."""
    realm = v["domain"].upper()
    kdc = kdc or v["fqdn"]
    cfg = (f"{MARK_B}\n"
           f"[libdefaults]\n"
           f"    default_realm = {realm}\n"
           f"    dns_lookup_realm = false\n"
           f"    dns_lookup_kdc = true\n"
           f"    ticket_lifetime = 24h\n"
           f"    renew_lifetime = 7d\n"
           f"    forwardable = true\n"
           f"    rdns = false\n"
           f"[realms]\n"
           f"    {realm} = {{\n"
           f"        kdc = {kdc}\n"
           f"        admin_server = {kdc}\n"
           f"    }}\n"
           f"[domain_realm]\n"
           f"    .{v['domain']} = {realm}\n"
           f"    {v['domain']} = {realm}\n"
           f"{MARK_E}\n")
    backup = None
    try:
        old = KRB5.read_text()
    except OSError:
        # krb5-user pas encore installe : on cree le fichier (dpkg le
        # creera autrement par-dessus — cf. ordre des etapes de setup)
        old = ""
    try:
        if old.strip():
            bak = Path(str(KRB5) + ".infraos-bak")
            if not bak.exists():
                bak.write_text(old)
                backup = str(bak)
        if MARK_B in old and MARK_E in old:
            head, rest = old.split(MARK_B, 1)
            _, tail = rest.split(MARK_E, 1)
            KRB5.write_text(head + cfg + tail.lstrip("\n"))
        elif old.strip():
            KRB5.write_text(old.rstrip("\n") + "\n" + cfg)
        else:
            KRB5.write_text(cfg)
    except OSError as e:
        raise ValueError(f"ecriture /etc/krb5.conf impossible: {e}")
    return {"file": str(KRB5), "backup": backup, "realm": realm}


def _resolv_forwarder() -> str:
    """Upstream DNS pour Samba : d'abord resolv.conf live, puis la sauvegarde
    .infraos-bak (apres un 1er provision, resolv.conf ne contient plus que
    127.0.0.1 — sans fallback on declarerait le DC comme son propre forwarder).
    127.0.0.1/::1 exclus (boucle)."""
    for candidate in (RESOLV, Path(str(RESOLV) + ".infraos-bak")):
        try:
            for line in candidate.read_text().splitlines():
                p = line.split()
                if len(p) >= 2 and p[0] == "nameserver" and p[1] not in ("127.0.0.1", "::1"):
                    return p[1]
        except OSError:
            continue
    return "1.1.1.1"


def _listening_ports() -> set[int]:
    ports: set[int] = set()
    try:
        for path in ("/proc/net/tcp", "/proc/net/tcp6"):
            with open(path) as f:
                for line in f.read().splitlines()[1:]:
                    parts = line.split()
                    if len(parts) > 3 and parts[3] == "0A":
                        ports.add(int(parts[1].split(":")[1], 16))
    except OSError:
        pass
    return ports


def _svc(name: str) -> str:
    if name not in AD_SERVICES:
        raise ValueError(f"service inconnu: {name}")
    r = run("systemctl", "is-active", name, caller="identity.svc")
    return (r.out.strip() or "unknown").splitlines()[0]


def preflight(v: dict) -> dict:
    """Spec §4 : verifs systeme AVANT creation du domaine. Ne modifie rien."""
    checks: list[dict] = []

    def add(name: str, status: str, detail: str):
        checks.append({"check": name, "status": status, "detail": detail})

    # hostname / FQDN
    try:
        os_host = socket.gethostname()
        add("hostname", "ok" if os_host == v["hostname"] else "warn",
            f"OS={os_host}, demande={v['hostname']}"
            + ("" if os_host == v["hostname"] else " (sera change par hostnamectl)"))
    except Exception as e:
        add("hostname", "error", str(e))
    # resolution du FQDN (via /etc/hosts apres ecriture — avant : best effort)
    try:
        socket.getaddrinfo(v["fqdn"], None)
        add("fqdn", "ok", f"{v['fqdn']} resout")
    except OSError:
        add("fqdn", "warn", f"{v['fqdn']} ne resout pas encore (bloc /etc/hosts a ecrire)")
    # IP locale ?
    local_ip = ""
    try:
        import socket as _sock

        import psutil
        for name, addrs in psutil.net_if_addrs().items():
            for a in addrs:
                # psutil peut renvoyer int (2), IntEnum ou str — les 3 = AF_INET
                if (a.family == _sock.AF_INET
                        or str(a.family) in ("AddressFamily.AF_INET", "2")) \
                        and a.address == v["ip"]:
                    local_ip = a.address
    except Exception:
        pass
    add("ip", "ok" if local_ip else "warn",
        f"{v['ip']} presente sur une interface" if local_ip else
        f"{v['ip']} absente des interfaces locales (verifier la config reseau)")
    # /etc/hosts actuel
    try:
        hosts_txt = HOSTS.read_text()
        add("hosts", "ok" if v["fqdn"] in hosts_txt else "warn",
            "entree presente" if v["fqdn"] in hosts_txt else "entree absente (sera ecrite)")
    except OSError as e:
        add("hosts", "error", str(e))
    # resolution DNS sortante
    try:
        socket.getaddrinfo("deb.debian.org", 443)
        add("dns_sortant", "ok", "resolution sortante OK")
    except OSError:
        add("dns_sortant", "warn", "resolution sortante impossible")
    # connectivite : route par defaut
    try:
        from . import netconfig as nc
        gw = nc.gateways()
        add("passerelle", "ok" if gw else "warn",
            f"defaut via {', '.join(gw)}" if gw else "aucune route par defaut")
    except Exception as e:
        add("passerelle", "warn", str(e))
    # ports AD
    busy = sorted(p for p in (53, 88, 135, 389, 445, 464, 636, 3268, 3269)
                  if p in _listening_ports())
    if not busy:
        add("ports", "ok", "ports AD libres")
    else:
        named_busy = 53 in busy and _svc("named") == "active"
        add("ports", "warn" if named_busy else "error",
            f"occupes: {busy}"
            + (" — named actif (sera arrete avec confirm, Samba devient autoritaire)"
               if named_busy else ""))
    # synchro horaire
    try:
        r = run("timedatectl", "show", caller="identity.time")
        ntp = "NTPSynchronized=yes" in r.out
        add("heure", "ok" if ntp else "warn",
            "NTP synchronise" if ntp else "NTP non synchronise (Kerberos exige <5min de skew)")
    except Exception as e:
        add("heure", "warn", str(e))
    # paquets
    from . import packages as pkg
    samba_ok = pkg.is_installed("samba").get("installed")
    add("samba", "ok" if samba_ok else "warn",
        "paquet samba installe" if samba_ok else "paquet samba absent (sera installe)")
    krb5_ok = pkg.is_installed("krb5-user").get("installed")
    add("krb5", "ok" if krb5_ok else "warn",
        "krb5-user installe" if krb5_ok else "krb5-user absent (sera installe)")
    # deja provisionne ?
    if is_provisioned():
        add("provision", "error", "domaine deja configure (sam.ldb present) — non reconfigurable")
    else:
        add("provision", "ok", "non provisionne")
    ok = all(c["status"] != "error" for c in checks)
    return {"ok": ok, "checks": checks,
            "changes": [
                f"/etc/hosts : ajout du bloc {MARK_B} ({v['ip']} {v['fqdn']})",
                "installation paquets samba / krb5-user si absents",
                "/etc/krb5.conf : configuration du realm " + v["domain"].upper(),
                "arret des services smbd/nmbd/winbind (mode standalone -> AD DC)",
                "arret de named si occupe (Samba DNS devient autoritaire pour le realm)",
                "smb.conf standalone : sauvegarde + retrait (provision le regenere)",
                "provisionnement samba-tool domain provision (Samba AD DC)",
                "demarrage + enable du service samba-ad-dc",
                "/etc/resolv.conf : nameserver 127.0.0.1 (le DC est son resolver)",
            ]}


def _wait_port(port: int, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port in _listening_ports():
            return True
        time.sleep(1)
    return False


def setup(body: dict, actor: str = "api") -> dict:
    """Creation du domaine (spec §36) — etapes tracees, auditees, robustes.

    body: domain, netbios, hostname, ip, admin_password, admin_user,
          stop_named (bool), confirm (bool).
    """
    from . import apt as apt_mod
    from . import event_manager as em

    v = validate_inputs(body.get("domain", ""), body.get("netbios", ""),
                        body.get("hostname", ""), body.get("ip", ""))
    admin_user = (body.get("admin_user") or "Administrator").strip() or "Administrator"
    if not re.match(r"^[A-Za-z0-9._-]{1,64}$", admin_user):
        raise ValueError(f"administrateur invalide: {admin_user!r}")
    admin_password = body.get("admin_password") or ""
    if len(admin_password) < 8:
        raise ValueError("mot de passe administrateur : 8 caracteres minimum")
    stop_named = bool(body.get("stop_named", True))
    confirm = bool(body.get("confirm", False))

    if is_provisioned():
        raise ValueError("domaine deja configure (sam.ldb present)")
    pf = preflight(v)
    if not pf["ok"]:
        return {"status": "error", "steps": [], "preflight": pf,
                "detail": "verifications preflight en echec"}
    if not confirm:
        # retourne le plan sans rien modifier (etape Review de l'assistant)
        return {"status": "planned", "preflight": pf, "changes": pf["changes"],
                "detail": "confirm:true requis pour appliquer"}

    steps: list[dict] = []

    def step(name: str, fn) -> bool:
        try:
            detail = fn() or "OK"
            steps.append({"step": name, "status": "ok", "detail": str(detail)[:800]})
            return True
        except Exception as e:
            steps.append({"step": name, "status": "error", "detail": str(e)[:800]})
            return False

    def s_restart(name: str) -> str:
        if name not in AD_SERVICES:
            raise ValueError(f"service inconnu: {name}")
        r = run("systemctl", "stop", name, caller="identity.setup")
        return f"stop {name} rc={r.rc}"

    # 1. hostname
    def _hostname():
        os_host = socket.gethostname()
        if os_host != v["hostname"]:
            r = run("hostnamectl", "set-hostname", v["hostname"], caller="identity.setup")
            if r.rc != 0:
                raise ValueError(f"hostnamectl: {r.out[:200]}")
            return f"hostname {os_host} -> {v['hostname']}"
        return "hostname deja correct"
    if not step("hostname", _hostname):
        return {"status": "error", "steps": steps, "detail": "etape hostname en echec"}

    # 2. /etc/hosts
    if not step("hosts", lambda: write_hosts(v)):
        return {"status": "error", "steps": steps, "detail": "etape /etc/hosts en echec"}

    # 3. secrets dir (§23)
    step("secrets", lambda: f"repertoire {ensure_secret_dir()} (0700)")

    # 4. paquets (avant krb5.conf : dpkg creerait /etc/krb5.conf par-dessus)
    def _packages():
        from . import packages as pkg
        missing = [p for p in ("samba", "krb5-user", "chrony")
                   if not pkg.is_installed(p).get("installed")]
        if not missing:
            return "deja installes"
        res = apt_mod.install_packages(missing, caller="identity.setup")
        if res["rc"] != 0:
            raise ValueError(f"apt install {missing}: {res['detail'][-300:]}")
        return f"installes: {missing}"
    if not step("paquets", _packages):
        return {"status": "error", "steps": steps, "detail": "installation paquets en echec"}

    # 5. /etc/krb5.conf (apres krb5-user, notre bloc marque reste maitre)
    if not step("krb5.conf", lambda: write_krb5(v)):
        return {"status": "error", "steps": steps, "detail": "etape krb5.conf en echec"}

    # 6. arret services standalone / DNS conflit
    stopped_named = False

    def _stop_services():
        nonlocal stopped_named
        stopped = []
        for svc in ("smbd", "nmbd", "winbind"):
            if _svc(svc) in ("active", "activating"):
                stopped.append(s_restart(svc))
        if 53 in _listening_ports() and _svc("named") == "active":
            if not stop_named:
                raise ValueError("port 53 occupe par named — stop_named:true requis")
            stopped.append(s_restart("named"))
            stopped_named = True
        return "; ".join(stopped) or "aucun service a arreter"
    if not step("arret_services", _stop_services):
        return {"status": "error", "steps": steps, "detail": "arret services en echec"}

    # 7. provisionnement (mot de passe masque dans l'audit via secret_args)
    def _clear_standalone_conf():
        """smb.conf standalone empeche le provision (server role != DC).
        Detection sur la LIGNE REELLE 'server role=' (pas les commentaires)."""
        conf = Path("/etc/samba/smb.conf")
        if not conf.exists():
            return "pas de smb.conf"
        role = ""
        for line in conf.read_text().splitlines():
            s = line.strip()
            # lignes reelles uniquement (les commentaires commencent par # ou ;)
            if not s.startswith(("#", ";")) and s.lower().startswith("server role") \
                    and "=" in s:
                role = s.split("=", 1)[1].strip().lower()
                break
        if role.startswith("active directory"):
            return "smb.conf deja AD DC"
        bak = Path(str(conf) + ".infraos-bak")
        if not bak.exists():
            bak.write_text(conf.read_text())
        conf.unlink()
        return (f"smb.conf (role={role or 'non precise'}) sauvegarde -> {bak} ; "
                "provision en regenerera un AD DC")
    if not step("smb.conf", _clear_standalone_conf):
        return {"status": "error", "steps": steps, "detail": "smb.conf en echec"}

    def _provision():
        ap = f"--adminpass={admin_password}"
        args = ["domain", "provision",
                f"--realm={v['domain'].upper()}",
                f"--domain={v['netbios']}",
                "--server-role=dc",
                "--dns-backend=SAMBA_INTERNAL",
                f"--host-name={v['hostname']}",
                f"--host-ip={v['ip']}",
                f"--dns-forwarder={_resolv_forwarder()}",
                ap]
        r = run("samba-tool", *args, timeout=300, caller="identity.setup",
                secret_args=(ap,))
        if r.rc != 0:
            raise ValueError(f"samba-tool provision rc={r.rc}: {r.out[-500:]}")
        return "Samba AD DC provisionne"
    if not step("provision", _provision):
        return {"status": "error", "steps": steps, "detail": "provisionnement en echec"}

    # 8. persistance base
    def _persist():
        from .db import get_session
        from .models import IdentityDomain
        s = get_session()
        try:
            row = s.query(IdentityDomain).filter_by(realm=v["domain"]).first()
            if not row:
                row = IdentityDomain(realm=v["domain"])
                s.add(row)
            row.netbios = v["netbios"]
            row.dc_hostname = v["hostname"]
            row.dc_fqdn = v["fqdn"]
            row.dc_ip = v["ip"]
            row.dns_backend = "SAMBA_INTERNAL"
            row.status = "active"
            row.admin_user = admin_user
            row.hosts_written = True
            row.krb5_written = True
            row.named_stopped = stopped_named
            row.provisioned_at = datetime.now(timezone.utc)
            row.created_by = actor
            s.commit()
            return f"domaine {v['domain']} enregistre en base"
        finally:
            s.close()
    if not step("base", _persist):
        return {"status": "error", "steps": steps, "detail": "persistance en echec"}

    # 9. service samba-ad-dc
    def _service():
        out = []
        r = run("systemctl", "enable", "samba-ad-dc", caller="identity.setup")
        out.append(f"enable rc={r.rc}")
        r = run("systemctl", "start", "samba-ad-dc", caller="identity.setup")
        out.append(f"start rc={r.rc}")
        if r.rc != 0:
            raise ValueError(f"demarrage samba-ad-dc: {r.out[-300:]}")
        if not _wait_port(389, 40):
            raise ValueError("port LDAP 389 non joignable apres 40s")
        out.append("LDAP 389 OK")
        if not _wait_port(88, 10):
            raise ValueError("port Kerberos 88 non joignable")
        out.append("Kerberos 88 OK")
        if not (SYSVOL / v["domain"]).exists() and not SYSVOL.exists():
            raise ValueError("SYSVOL absent")
        out.append("SYSVOL OK" if SYSVOL.exists() else "SYSVOL partiel")
        return "; ".join(out)
    if not step("service", _service):
        return {"status": "error", "steps": steps, "detail": "demarrage service en echec"}

    # 9bis. resolv.conf -> 127.0.0.1 (securise : service deja up sur 53)
    if not step("resolv.conf", lambda: write_resolv(v)):
        return {"status": "error", "steps": steps, "detail": "resolv.conf en echec"}

    # 10. audit
    try:
        em.publish("identity.domain.setup", actor, f"domain={v['domain']} netbios={v['netbios']}",
                   resource=v["domain"])
    except Exception:
        pass
    return {"status": "done", "steps": steps, "preflight": pf,
            "domain": v["domain"], "netbios": v["netbios"], "fqdn": v["fqdn"],
            "ip": v["ip"], "detail": "Domain Controller configure"}


def domain_info() -> dict:
    """Infos domaine : base + samba-tool domain info (si provisionne)."""
    row = domain_row()
    out: dict = {"provisioned": is_provisioned()}
    if row:
        out.update({"domain": row.realm, "netbios_name": row.netbios,
                    "hostname": row.dc_hostname, "fqdn": row.dc_fqdn,
                    "ip": row.dc_ip, "status": row.status,
                    "admin_user": row.admin_user,
                    "provisioned_at": str(row.provisioned_at or ""),
                    "created_by": row.created_by})
    if is_provisioned():
        r = run("samba-tool", "domain", "info", "127.0.0.1", timeout=20,
                caller="identity.info")
        info: dict = {}
        if r.rc == 0:
            for line in r.out.splitlines():
                if ":" in line:
                    k, val = line.split(":", 1)
                    info[k.strip().lower().replace(" ", "_")] = val.strip()
        out["live"] = info
        out["domain"] = out.get("domain") or info.get("domain", "")
    return out


def backup(actor: str = "api") -> dict:
    """§29 : sauvegarde Samba (private/ + sysvol metadata) avant operation
    destructive. tar allow-liste, argv fixe."""
    from . import event_manager as em
    if not is_provisioned():
        raise ValueError("domaine non provisionne — rien a sauvegarder")
    dest_dir = Path("/var/backups/infraos")
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"samba-identity-{stamp}.tar.gz"
    r = run("tar", "-czf", str(dest), "-C", "/var/lib/samba", "private",
            "state.shares", caller="identity.backup", timeout=300)
    if r.rc != 0 and not dest.exists():
        # sysvol peut manquer : archive private seule
        r = run("tar", "-czf", str(dest), "-C", "/var/lib/samba", "private",
                caller="identity.backup", timeout=300)
    if not dest.exists():
        raise ValueError(f"sauvegarde impossible: {r.out[-300:]}")
    try:
        dest.chmod(0o600)
    except OSError:
        pass
    try:
        em.publish("identity.domain.backup", actor, str(dest), resource=str(dest))
    except Exception:
        pass
    return {"backup": str(dest), "size": dest.stat().st_size, "rc": r.rc}


def uninstall_guard(confirm: bool, actor: str = "api") -> dict:
    """§29 : un DC ne se desinstalle pas comme un module simple."""
    from . import event_manager as em
    if not is_provisioned():
        return {"provisioned": False, "detail": "aucun domaine — desinstallation standard"}
    if not confirm:
        return {"provisioned": True, "status": "blocked", "warning":
                "Ce serveur est configure comme Domain Controller. La suppression "
                "du module Identity peut detruire les services de domaine et les "
                "donnees d'authentication. confirm:true requis "
                "(backup conseille: POST /api/v1/identity/domain/backup).",
                "changes": ["arret samba-ad-dc", "suppression de la base SAM (sam.ldb)",
                            "suppression de /var/lib/samba/sysvol",
                            "perte definitive des comptes de domaine"]}
    bak = backup(actor)
    em.publish("identity.domain.uninstall", actor, f"backup={bak['backup']}")
    return {"provisioned": True, "status": "ready_for_uninstall", "backup": bak,
            "detail": "sauvegarde effectuee — l'operateur confirme ensuite "
                      "l'uninstall dans Modules"}
