"""Central allow-list executor — philo: JAMAIS de shell arbitraire depuis le Web.

Toute commande systeme passee par l'API/UI DOIT passer par run() ci-dessous.
- shell=False toujours, argv liste fermee, timeout impose.
- Seules les binaires et sous-commandes declares dans ALLOWED sont executables.
- Chaque appel est journalise (audit.log) avec l'appelant.
- Aucune entree utilisateur n'est jamais interpretee par un shell.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

# Binaire -> sous-commandes figees autorisees (argv exact, sans glob).
# Natifs Debian/Linux couverts: systemd, apt, dpkg, journald, nftables, iproute2.
ALLOWED: dict[str, set[str]] = {
    "systemd-detect-virt": set(),  # sans argument
    "systemctl": {"is-active", "is-enabled", "status",
                  "start", "stop", "restart", "enable", "disable"},
    "ip": {"addr", "route", "link"},
    "apt-get": {"check", "install", "remove", "update", "full-upgrade"},
    "apt": {"list", "show"},
    "apt-cache": {"policy"},
    "dpkg-query": {"-W"},
    "dpkg": {"-l", "-s"},
    "journalctl": {"--no-pager"},
    "nft": {"list"},
    "named-checkconf": {"/etc/bind/named.conf"},
    "rndc": {"reload", "status"},
    "kea-dhcp4": {"-t"},
    "networkctl": {"reload", "status"},
    "wg": {"genkey", "genpsk", "show"},
    "nmap": {"-sn", "-F", "-O"},
    "testparm": {"-s"},
    # Identity & Domain Controller (Samba AD DC — jamais de shell libre)
    "samba-tool": {"domain", "user", "group", "computer", "ou", "dns"},
    "dig": set(),       # requetes DNS locales (aucune auth — 127.0.0.1)
    "kinit": set(),      # argv valide par identity_samba avant appel
    "klist": set(),
    "kdestroy": set(),
    "timedatectl": {"show", "status"},
    "hostnamectl": {"set-hostname", "status"},
    "tar": {"-czf", "-tzf"},
}

TIMEOUT = 15


@dataclass
class ExecResult:
    rc: int
    out: str


class ForbiddenCommand(Exception):
    pass


def run(binary: str, *args: str, timeout: int = TIMEOUT,
        caller: str = "api", stdin_data: str | None = None,
        secret_args: tuple[str, ...] = ()) -> ExecResult:
    """Execute une commande allow-listee. Leve ForbiddenCommand sinon.

    stdin_data : entree standard (ex. mot de passe kinit) — JAMAIS dans argv.
    secret_args : fragments d'argv exacts a masquer dans l'audit (ex. --newpassword=..).
    """
    allowed_sub = ALLOWED.get(binary)
    if allowed_sub is None:
        raise ForbiddenCommand(f"binaire interdit: {binary}")
    for a in args:
        # arguments dangereux refuses (shell metachars, options non listees en position 0).
        # '$' admis UNIQUEMENT en suffixe (principaux machine AD : "WS01$") —
        # jamais en milieu/debut (pas de substitution $VAR/$() possible).
        if any(c in a for c in (";", "&", "|", "`", "\n", "\r")) \
                or "$" in a.rstrip("$"):
            raise ForbiddenCommand(f"argument dangereux refuse: {a!r}")
    if allowed_sub and (not args or args[0] not in allowed_sub):
        raise ForbiddenCommand(f"sous-commande interdite: {binary} {args[:1]}")
    exe = shutil.which(binary)
    if not exe:
        return ExecResult(127, f"{binary} introuvable")
    display = tuple("***" if a in secret_args else a for a in args)
    try:
        p = subprocess.run([exe, *args], capture_output=True, text=True,
                           timeout=timeout, shell=False, input=stdin_data)
        out = (p.stdout + p.stderr).strip()
    except Exception as e:  # timeout, permission...
        try:
            from .audit import audit
            audit(f"exec-fail {binary} {list(display)} caller={caller} err={e}")
        except Exception:
            pass
        return ExecResult(1, str(e))
    try:
        from .audit import audit
        audit(f"exec {binary} {list(display)} caller={caller} rc={p.returncode}")
    except Exception:
        pass
    return ExecResult(p.returncode, out)
