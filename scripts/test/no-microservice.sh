#!/bin/bash
# Garde-fou ADR-001: un seul FastAPI() = un seul monolithe (pas de microservices).
set -u
N=$(grep -rn "FastAPI(" --include="*.py" backend agent 2>/dev/null | grep -v __pycache__ | grep -v "/tests/" | wc -l)
echo "FastAPI() count: $N"
[ "$N" -eq 1 ] && echo "OK: monolithe (1 app)" || { echo "KO: $N apps"; exit 1; }
