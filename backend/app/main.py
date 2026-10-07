"""InfraOS API - FastAPI entrypoint.

Philo: API documentee (OpenAPI sur /docs), journalisation complete,
aucune commande shell arbitraire — routers -> core.exec allow-list uniquement.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
_BASE = Path(__file__).resolve().parent  # backend/app
for _p in (_BASE, _BASE / "api", _BASE / "core",
           Path("/opt/infraos/backend/app"),
           Path("/opt/infraos/backend/app/api"),
           Path("/opt/infraos/backend/app/core")):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import system, services, modules, network, users, updates, auth, jobs, logs, config, events, groups, domain, dns, dhcp, firewall, vpn, ipam, discovery, monitoring, shares, backup, security, roles, identity
from audit_middleware import AuditMiddleware
from secure_headers import SecureHeadersMiddleware
from infraos.config import load_settings as _settings

_settings_cached = _settings()

app = FastAPI(title="InfraOS API", version="0.1.0",
              description="Infrastructure Server OS - API centralisee (GPLv3, 100% open source)",
              docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json")

app.add_middleware(AuditMiddleware)
app.add_middleware(SecureHeadersMiddleware)

_cors = [o.strip() for o in os.getenv("INFRAOS_CORS_ORIGINS", _settings_cached.cors_origins).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/api/health")
def health_legacy():
    return _health_body()


@app.get("/api/v1/health")
def health_v1():
    """Sante canonique versionnee (spec point 24)."""
    return _health_body()


def _health_body():
    from infraos.cache import backend as cache_backend
    from infraos.config import load_settings
    url = os.getenv("INFRAOS_DB_URL", load_settings().db_url)
    backend = "postgres" if url.startswith("postgres") else "sqlite"
    return {"status": "ok", "service": "infraos-api", "version": "0.2.0",
            "db": backend, "cache": cache_backend()}


@app.on_event("startup")
def _startup():
    from infraos.config import load_settings
    from infraos.db import init_db, get_session
    from infraos.models import User
    from infraos.security import hash_password
    s = load_settings()
    init_db(os.getenv("INFRAOS_DB_URL", s.db_url))
    db = get_session()
    try:
        try:
            from infraos.permissions import seed_rbac
            seed_rbac(db)
        except Exception:
            pass
        if not db.query(User).filter_by(username=s.admin_user).first():
            db.add(User(username=s.admin_user,
                        password_hash=hash_password(os.getenv("INFRAOS_ADMIN_PASSWORD", s.admin_password)),
                        role="admin", display_name="Administrateur"))
            db.commit()
        else:
            # bootstrap post-0013 : s'il n'existe aucun superadmin,
            # le compte initial admin est promu (une seule fois)
            from infraos.models import UserRole, Role
            has_sa = db.query(User).filter_by(role="superadmin").first()
            if not has_sa:
                has_sa = (db.query(User).join(UserRole, UserRole.user_id == User.id)
                          .join(Role, Role.id == UserRole.role_id)
                          .filter(Role.name == "superadmin").first())
            u = db.query(User).filter_by(username=s.admin_user).first()
            if not has_sa and u is not None and u.role == "admin":
                u.role = "superadmin"
                db.commit()
    finally:
        db.close()


app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])


app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(services.router, prefix="/api/v1/services", tags=["services"])
app.include_router(modules.router, prefix="/api/v1/modules", tags=["modules"])
app.include_router(network.router, prefix="/api/v1/network", tags=["network"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(updates.router, prefix="/api/v1/updates", tags=["updates"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])
app.include_router(config.router, prefix="/api/v1/config", tags=["config"])
app.include_router(events.router, prefix="/api/v1/events", tags=["events"])
app.include_router(groups.router, prefix="/api/v1/groups", tags=["groups"])
app.include_router(domain.router, prefix="/api/v1/domain", tags=["domain"])
app.include_router(dns.router, prefix="/api/v1/dns", tags=["dns"])
app.include_router(dhcp.router, prefix="/api/v1/dhcp", tags=["dhcp"])
app.include_router(firewall.router, prefix="/api/v1/firewall", tags=["firewall"])
app.include_router(vpn.router, prefix="/api/v1/vpn", tags=["vpn"])
app.include_router(ipam.router, prefix="/api/v1/ipam", tags=["ipam"])
app.include_router(discovery.router, prefix="/api/v1/discovery", tags=["discovery"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])
app.include_router(shares.router, prefix="/api/v1/shares", tags=["shares"])
app.include_router(backup.router, prefix="/api/v1/backup", tags=["backup"])
app.include_router(security.router, prefix="/api/v1/security", tags=["security"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["roles"])
app.include_router(identity.router, prefix="/api/v1/identity", tags=["identity"])
