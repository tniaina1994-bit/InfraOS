"""Mises a jour systeme — 100% APT Debian natif, rien de reimplemente.

Philo: apt/dpkg comme base (jamais remplaces). Lecture (check/list/info)
libre ; installation explicite admin, auditee, historisee (update_runs).
"""
from __future__ import annotations
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from .exec import run
from .logging_conf import get_logger

log = get_logger("infraos.updates")
_PKG = re.compile(r"^[a-z0-9][a-z0-9+.:~-]*$")


def check_updates() -> dict:
    """Retourne nb de paquets upgradables via apt (sans modifier le systeme)."""
    apt_get = shutil.which("apt-get")
    if not apt_get:
        return {"backend": "none", "pending": 0, "detail": "apt-get absent (dev Windows?)"}
    try:
        subprocess.run([apt_get, "update", "-qq"], capture_output=True,
                       timeout=120, shell=False)
        apt = shutil.which("apt")
        if apt:
            p = subprocess.run([apt, "list", "--upgradable"],
                               capture_output=True, text=True, timeout=60, shell=False)
            lines = [l for l in p.stdout.splitlines()
                     if l and not l.startswith("Listing")]
            pkgs = [l.split("/")[0] for l in lines if "/" in l]
            return {"backend": "apt", "pending": len(pkgs),
                    "packages": pkgs[:50], "truncated": len(pkgs) > 50}
        # fallback: simulation dry-run
        p = subprocess.run([apt_get, "-s", "upgrade"], capture_output=True,
                           text=True, timeout=60, shell=False)
        n = len(re.findall(r"^Inst ", p.stdout, re.M))
        return {"backend": "apt-get -s", "pending": n}
    except Exception as e:
        log.error("check_updates: %s", e)
        return {"backend": "apt", "pending": 0, "error": str(e)}


def list_updates() -> dict:
    """Detail des paquets upgradables (nom/version/architecture)."""
    base = check_updates()
    pkgs = base.get("packages", [])
    r = run("apt", "list", "--upgradable", timeout=60, caller="updates.list")
    detail = []
    for line in r.out.splitlines():
        if not line or line.startswith("Listing") or "/" not in line:
            continue
        name = line.split("/")[0]
        m = re.search(r"(\S+)\s+(\S+)\s+(\S+)", line)
        detail.append({"name": name, "info": (m.group(0) if m else line)[:200]})
    return {"pending": base.get("pending", 0), "packages": pkgs, "detail": detail[:100]}


def security_updates() -> dict:
    """Sous-ensemble issu des depots security (apt-cache policy)."""
    base = check_updates()
    sec = []
    for pkg in base.get("packages", [])[:200]:
        if not _PKG.match(pkg or ""):
            continue
        r = run("apt-cache", "policy", pkg, timeout=15, caller="updates.security")
        if "security" in r.out.lower():
            sec.append(pkg)
    return {"pending_security": len(sec), "packages": sec}


def package_info(package: str) -> dict:
    if not _PKG.match(package or ""):
        raise ValueError(f"paquet invalide: {package}")
    r = run("apt", "show", package, timeout=30, caller="updates.info")
    if r.rc != 0:
        r = run("dpkg", "-s", package, timeout=15, caller="updates.info")
    return {"package": package, "rc": r.rc, "info": r.out[:3000]}


def install_updates(packages: list[str], actor: str = "api", kind: str = "packages") -> dict:
    """Installation explicite (admin, auditee, historisee). Paquets valides
    uniquement ; jamais de full-upgrade aveugle sans liste."""
    from . import apt as apt_mod
    from .db import get_session
    from .models import UpdateRun
    clean = [p for p in (packages or []) if _PKG.match(p or "")]
    if len(clean) != len(packages or []) or not clean:
        raise ValueError("liste de paquets explicite requise (noms Debian valides)")
    s = get_session()
    try:
        run_row = UpdateRun(kind=kind, packages=json.dumps(clean), status="running",
                            actor=actor)
        s.add(run_row)
        s.commit()
        rid = run_row.id
    finally:
        s.close()
    res = apt_mod.install_packages(clean, caller=f"updates.{actor}")
    status = "done" if res["rc"] == 0 else "error"
    s = get_session()
    try:
        row = s.get(UpdateRun, rid)
        row.status = status
        row.log = res["detail"][-8000:]
        row.finished_at = datetime.now(timezone.utc)
        s.commit()
    finally:
        s.close()
    try:
        from .audit import audit
        audit("updates.install", actor=actor, resource=",".join(clean)[:255],
              result="SUCCESS" if status == "done" else "FAILURE")
    except Exception:
        pass
    return {"run_id": rid, "status": status, **res}


def history(limit: int = 20) -> list[dict]:
    from .db import get_session
    from .models import UpdateRun
    s = get_session()
    try:
        rows = (s.query(UpdateRun).order_by(UpdateRun.id.desc())
                .limit(max(1, min(int(limit), 100))).all())
        return [{"id": r.id, "kind": r.kind, "status": r.status,
                 "packages": json.loads(r.packages or "[]"),
                 "actor": r.actor, "created_at": str(r.created_at),
                 "log": (r.log or "")[-2000:]} for r in rows]
    finally:
        s.close()


# --- Sources APT (lecture/edition pilotees, fichiers 10-infraos-* uniquement) ---

_SOURCES_DIR = Path("/etc/apt/sources.list.d")
_KEYRING_DIR = Path("/etc/apt/keyrings")
_NAME = re.compile(r"^[a-z0-9][a-z0-9.-]{0,62}$")
_SUITE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9./_-]*$")
_COMP = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 ./+-]*$")


def _parse_oneline(path: Path, managed: bool) -> list[dict]:
    out = []
    try:
        text = path.read_text()
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3 or parts[0] not in ("deb", "deb-src"):
            continue
        opts, uri, suite = "", parts[1], parts[2]
        comps = parts[3:]
        if uri.startswith("[") and "]" in uri:
            opts, uri = uri[1:].split("]", 1)[0], uri.split("]", 1)[1]
        out.append({
            "name": path.stem if path.name != "sources.list" else "main",
            "file": str(path), "uri": uri, "suite": suite,
            "components": " ".join(comps),
            "signed": "trusted=yes" not in opts,
            "managed": managed,
        })
    return out


def _parse_deb822(path: Path) -> list[dict]:
    out = []
    try:
        text = path.read_text()
    except OSError:
        return out
    for stanza in text.split("\n\n"):
        fields: dict[str, str] = {}
        for line in stanza.splitlines():
            if not line or line.startswith("#") or line.startswith(" "):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip()
        if "URIs" not in fields or fields.get("Types", "deb").split()[0] != "deb":
            continue
        out.append({
            "name": path.stem, "file": str(path),
            "uri": fields["URIs"].split()[0],
            "suite": fields.get("Suites", "").split()[0] if fields.get("Suites") else "",
            "components": fields.get("Components", ""),
            "signed": "trusted=yes" not in stanza and bool(fields.get("Signed-By", True)),
            "managed": path.name.startswith("10-infraos-"),
        })
    return out


def list_sources() -> list[dict]:
    out = _parse_oneline(Path("/etc/apt/sources.list"), managed=False)
    if _SOURCES_DIR.is_dir():
        for f in sorted(_SOURCES_DIR.glob("*.list")):
            out += _parse_oneline(f, managed=f.name.startswith("10-infraos-"))
        for f in sorted(_SOURCES_DIR.glob("*.sources")):
            out += _parse_deb822(f)
    return out


def add_source(name: str, url: str, suite: str = "", components: str = "main",
               key_url: str = "") -> dict:
    """Cree /etc/apt/sources.list.d/10-infraos-<name>.list (+ cle optionnelle).
    Garde-fous : nom/URL/suite valides, URL http(s), cle https seule."""
    if not _NAME.match(name or ""):
        raise ValueError(f"nom de source invalide: {name!r}")
    if not url.startswith(("http://", "https://")) or any(c in url for c in " \t\n\"'"):
        raise ValueError("URL http(s) valide requise")
    if suite and not _SUITE.match(suite):
        raise ValueError(f"suite invalide: {suite!r}")
    if components and not _COMP.match(components):
        raise ValueError(f"composants invalides: {components!r}")
    _SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    target = _SOURCES_DIR / f"10-infraos-{name}.list"
    if target.exists():
        raise ValueError(f"la source {name} existe deja")
    opts = ""
    if key_url:
        if not key_url.startswith("https://") or any(c in key_url for c in " \t\n\"'"):
            raise ValueError("cle GPG : URL https seule acceptee")
        import urllib.request
        try:
            with urllib.request.urlopen(key_url, timeout=15) as resp:
                if resp.status != 200:
                    raise ValueError(f"telechargement cle HTTP {resp.status}")
                key = resp.read(65536)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"telechargement cle impossible: {e}")
        if not key:
            raise ValueError("cle GPG vide")
        _KEYRING_DIR.mkdir(parents=True, exist_ok=True)
        armored = key.lstrip().startswith(b"-----BEGIN")
        kpath = _KEYRING_DIR / f"infraos-{name}{'.asc' if armored else '.gpg'}"
        kpath.write_bytes(key)
        kpath.chmod(0o644)
        opts = f"[signed-by={kpath}] "
    target.write_text(f"deb {opts}{url} {suite}".rstrip()
                      + (f" {components}" if components else "") + "\n")
    log.info("apt source added: %s -> %s", name, target)
    return {"name": name, "file": str(target), "signed": bool(key_url)}


def remove_source(name: str) -> dict:
    """Supprime UNIQUEMENT un fichier cree par InfraOS (prefixe 10-infraos-)."""
    if not _NAME.match(name or ""):
        raise ValueError(f"nom de source invalide: {name!r}")
    removed = []
    target = _SOURCES_DIR / f"10-infraos-{name}.list"
    if target.exists():
        target.unlink()
        removed.append(str(target))
    for kpath in (_KEYRING_DIR / f"infraos-{name}.gpg",
                  _KEYRING_DIR / f"infraos-{name}.asc"):
        if kpath.exists():
            kpath.unlink()
            removed.append(str(kpath))
    if not removed:
        raise ValueError(f"source InfraOS introuvable: {name}")
    log.info("apt source removed: %s (%s)", name, removed)
    return {"removed": removed}


def full_upgrade(actor: str = "api") -> dict:
    """apt update + full-upgrade — admin, audite, historise (UpdateRun).
    Contrainte : commande allow-listee exec.py, argv fixe, shell=False."""
    from .db import get_session
    from .models import UpdateRun
    s = get_session()
    try:
        run_row = UpdateRun(kind="full-upgrade", packages="[]", status="running",
                            actor=actor)
        s.add(run_row)
        s.commit()
        rid = run_row.id
    finally:
        s.close()
    r1 = run("apt-get", "update", "-qq", timeout=300, caller=f"updates.{actor}")
    if r1.rc == 0:
        r2 = run("apt-get", "full-upgrade", "-y", timeout=1800,
                 caller=f"updates.{actor}")
        rc, out = r2.rc, r1.out + "\n" + r2.out
    else:
        rc, out = r1.rc, r1.out
    status = "done" if rc == 0 else "error"
    s = get_session()
    try:
        row = s.get(UpdateRun, rid)
        row.status = status
        row.log = out[-8000:]
        row.finished_at = datetime.now(timezone.utc)
        s.commit()
    finally:
        s.close()
    try:
        from .audit import audit
        audit("updates.full_upgrade", actor=actor, resource="system",
              result="SUCCESS" if status == "done" else "FAILURE")
    except Exception:
        pass
    return {"run_id": rid, "status": status, "rc": rc, "detail": out[-2000:]}
