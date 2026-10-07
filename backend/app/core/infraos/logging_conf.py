"""Journalisation complete: console + /var/log/infraos/infraos.log + journald."""
from __future__ import annotations
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE = Path(os.getenv("INFRAOS_LOG", "/var/log/infraos/infraos.log"))


def get_logger(name: str = "infraos") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(str(LOG_FILE), maxBytes=5_000_000, backupCount=3)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        pass  # dev Windows sans /var/log: console suffit
    return logger
