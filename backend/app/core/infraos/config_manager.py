# SPDX-License-Identifier: GPL-3.0-or-later
"""Gestion de la configuration — lecture + ecriture validee et auditee.

Classification (docs/CONFIGURATION.md) :
- systeme (/etc/infraos/*.yaml, modules/, network/, security/) : fichiers, versionnables ;
- applicative (DB) : modules.json runtime, jobs, zones... ;
- secrets (/etc/infraos/secrets/*, 0600) : JAMAIS en DB ni en log ;
- donnees (Postgres /var/lib/postgresql, /var/lib/infraos) ;
- runtime (/var/lib/infraos/*.json, /run) : reconstruit au besoin.
"""
from __future__ import annotations
import os
import re
from pathlib import Path
import yaml
from .config import load_settings
from .audit import audit

EDITABLE = {"jwt_expire_min": int}
REDACTED = {"jwt_secret", "admin_password"}
_URL_PASS = re.compile(r"(://[^:/@]+:)[^@]+(@)")
BASE = Path(os.getenv("INFRAOS_ETC", "/etc/infraos"))


def _redact_url(url: str) -> str:
    return _URL_PASS.sub(r"\1***\2", url)


STRUCTURE = ["modules", "security", "network", "secrets"]


def ensure_structure(base: Path | None = None) -> dict:
    """Cree /etc/infraos/{modules,security,network,secrets} + infraos.yaml
    (depuis config.yaml si present). Secrets dir en 0700."""
    b = base or BASE
    made = []
    for d in [b] + [b / s for s in STRUCTURE]:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            made.append(str(d))
    try:
        os.chmod(b / "secrets", 0o700)
    except OSError:
        pass
    main = b / "infraos.yaml"
    legacy = b / "config.yaml"
    if not main.exists() and legacy.exists():
        try:
            main.write_bytes(legacy.read_bytes())
            os.chmod(main, 0o600)
        except OSError:
            pass
    return {"base": str(b), "created": made, "infraos_yaml": main.exists()}


_SECRET_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def set_secret(name: str, value: str, base: Path | None = None) -> dict:
    if not _SECRET_NAME.match(name or ""):
        raise ValueError("nom de secret invalide")
    b = (base or BASE) / "secrets"
    b.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(b, 0o700)
    except OSError:
        pass
    p = b / name
    p.write_text(value)
    os.chmod(p, 0o600)
    audit("secret.set", actor="api", resource=f"secrets/{name}")
    return {"secret": name, "stored": True}


def module_config(name: str, patch: dict | None = None,
                  base: Path | None = None) -> dict:
    """Config par module (/etc/infraos/modules/<nom>.yaml). Lecture libre,
    ecriture validee (dict plat, cles alphanumeriques)."""
    if not re.match(r"^[a-z0-9-]+$", name or ""):
        raise ValueError("module invalide")
    b = (base or BASE) / "modules"
    b.mkdir(parents=True, exist_ok=True)
    p = b / f"{name}.yaml"
    current = {}
    if p.exists():
        try:
            current = yaml.safe_load(p.read_text()) or {}
        except OSError:
            pass
    if patch is None:
        return {"module": name, "config": current}
    if not isinstance(patch, dict):
        raise ValueError("patch dict requis")
    for k in patch:
        if not re.match(r"^[A-Za-z0-9_.-]{1,64}$", k):
            raise ValueError(f"cle invalide: {k}")
    current.update(patch)
    p.write_text(yaml.safe_dump(current, default_flow_style=False))
    audit("config.module", actor="api", resource=f"modules/{name}")
    return {"module": name, "config": current}


def show() -> dict:
    s = load_settings()
    d = s.model_dump()
    for k in REDACTED:
        if k in d:
            d[k] = "***"
    for k in ("db_url", "redis_url"):
        if isinstance(d.get(k), str):
            d[k] = _redact_url(d[k])
    d["config_files"] = [str(p) for p in
                         (Path("/etc/infraos/infraos.yaml"),
                          Path("/etc/infraos/config.yaml"), Path("config.yaml"))
                         if p.exists()]
    d["structure"] = ["modules", "security", "network", "secrets"]
    return d


def update(patch: dict, actor: str = "api") -> dict:
    bad = [k for k in patch if k not in EDITABLE]
    if bad:
        raise ValueError(f"cles non modifiables: {bad}")
    conv = {}
    for k, v in patch.items():
        try:
            conv[k] = EDITABLE[k](v)
        except (ValueError, TypeError):
            raise ValueError(f"{k}: type invalide")
    if "jwt_expire_min" in conv and not 5 <= conv["jwt_expire_min"] <= 1440:
        raise ValueError("jwt_expire_min: 5..1440")
    path = BASE / "infraos.yaml"
    legacy = BASE / "config.yaml"
    try:
        if path.exists():
            current = yaml.safe_load(path.read_text()) or {}
        elif legacy.exists():
            current = yaml.safe_load(legacy.read_text()) or {}
        else:
            current = {}
    except OSError:
        current = {}
    current.update(conv)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(current, default_flow_style=False))
        import os
        os.chmod(path, 0o600)
    except OSError as e:
        raise ValueError(f"persistance impossible: {e}")
    audit(f"config updated {sorted(conv)} actor={actor}")
    try:
        from .event_manager import publish
        publish("config.updated", actor, str(sorted(conv)))
    except Exception:
        pass
    return show()
