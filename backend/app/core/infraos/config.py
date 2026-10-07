"""Central config: /etc/infraos/config.yaml + env INFRAOS_*."""
from __future__ import annotations
import os
from pathlib import Path
import yaml
from pydantic import BaseModel


class Settings(BaseModel):
    data_dir: str = "/var/lib/infraos"
    # sqlite par defaut (dev LXC zero-friction), postgres en prod/ISO:
    # postgresql+psycopg2://infraos:SECRET@localhost:5432/infraos
    db_url: str = "sqlite:////var/lib/infraos/infraos.db"
    redis_url: str = "redis://127.0.0.1:6379/0"
    jwt_secret: str = "change-me-in-prod"
    jwt_expire_min: int = 60
    jwt_algorithm: str = "HS256"
    admin_user: str = "admin"
    admin_password: str = "change-me"  # surcharge via env INFRAOS_ADMIN_PASSWORD au seed
    password_min_length: int = 12
    password_require_digit: bool = True
    # CORS strict par defaut (dev local + LXC) ; "*" uniquement en dev explicite
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://192.168.10.39,http://192.168.10.50"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    # Integrations futures (stubs documentes, desactivees par defaut)
    ldap_url: str = ""
    ldap_base_dn: str = ""
    ad_domain: str = ""
    kerberos_realm: str = ""

# Ordre croissant de priorite (le dernier gagne) : defauts repo,
# legacy local, legacy systeme, canonique infraos.yaml, puis env.
CONFIG_PATHS = [Path("config/default-config.yaml"), Path("config.yaml"),
                Path("/etc/infraos/config.yaml"),
                Path("/etc/infraos/infraos.yaml")]


def load_settings() -> Settings:
    data: dict = {}
    for p in CONFIG_PATHS:
        if p.exists():
            data.update(yaml.safe_load(p.read_text()) or {})
    for k in list(Settings.model_fields.keys()):
        env = os.getenv("INFRAOS_" + k.upper())
        if env is not None:
            if k in ("jwt_expire_min", "api_port", "password_min_length"):
                try:
                    data[k] = int(env)
                except ValueError:
                    data[k] = env
            elif k in ("password_require_digit",):
                data[k] = env.lower() not in ("0", "false", "no")
            else:
                data[k] = env
    return Settings(**data)
