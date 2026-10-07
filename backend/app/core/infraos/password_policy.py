# SPDX-License-Identifier: GPL-3.0-or-later
"""Politique mot de passe —validee a la creation et au changement.

Parametres via Settings (env) : password_min_length (defaut 12),
password_require_digit (defaut true). Refus motives (pas de fuite).
"""
from __future__ import annotations


def check_password(password: str, min_length: int = 12,
                   require_digit: bool = True) -> None:
    if len(password or "") < min_length:
        raise ValueError(f"mot de passe trop court (min {min_length})")
    if require_digit and not any(c.isdigit() for c in password):
        raise ValueError("mot de passe doit contenir un chiffre")
    if len(set(password)) < 4:
        raise ValueError("mot de passe trop simple")
