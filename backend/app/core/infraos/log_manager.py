# SPDX-License-Identifier: GPL-3.0-or-later
"""Log Manager — facade (impl: journal.py + logging_conf.py + audit.py)."""
from .journal import read_logs  # noqa: F401
from .logging_conf import get_logger  # noqa: F401
from .audit import audit, AUDIT_LOG  # noqa: F401

__all__ = ["read_logs", "get_logger", "audit", "AUDIT_LOG"]
