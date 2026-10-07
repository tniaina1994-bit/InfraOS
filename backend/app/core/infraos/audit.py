"""Journal d'audit append-only: /var/log/infraos/audit.log (0600).

Format : <ts> user=<actor> action=<event> resource=<resource> ip=<ip> result=<result> <detail>
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import os

AUDIT_LOG = Path(os.getenv("INFRAOS_AUDIT_LOG", "/var/log/infraos/audit.log"))


def audit(event: str, actor: str = "system", resource: str = "",
          ip: str = "", result: str = "SUCCESS", detail: str = "") -> None:
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        line = (f"{ts} user={actor} action={event} resource={resource} "
                f"ip={ip} result={result} {event} {detail}".rstrip() + "\n")
        with open(AUDIT_LOG, "a") as f:
            f.write(line)
        try:
            os.chmod(AUDIT_LOG, 0o600)
        except OSError:
            pass
    except OSError:
        pass
