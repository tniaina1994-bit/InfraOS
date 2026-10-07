# SPDX-License-Identifier: GPL-3.0-or-later
"""Update Manager — facade (impl: updates.py sur APT natif)."""
from .updates import check_updates as check  # noqa: F401
from .updates import check_updates  # noqa: F401

__all__ = ["check", "check_updates"]
