#!/bin/bash
# Garde-fou philo: aucun shell arbitraire appelable depuis le Web.
# Echec si: shell=True, os.system, Popen, eval(), ou subprocess hors exec.py/updates.py
set -u
FAIL=0
echo "== grep motifs interdits (hors tests) =="
if grep -rnE "shell=True|os\.system\s*\(|eval\s*\(" --include="*.py" backend agent 2>/dev/null | grep -v __pycache__ | grep -v "/tests/"; then
  echo "KO: motif interdit trouve"; FAIL=1
else echo "OK: aucun shell=True/os.system/eval"; fi
if grep -rln "Popen" --include="*.py" backend agent 2>/dev/null | grep -v __pycache__ | grep -v "/tests/"; then
  echo "KO: Popen trouve"; FAIL=1
else echo "OK: pas de Popen"; fi
echo "== subprocess confine (argv fixes, pas d'entree shell) =="
# subprocess autorise UNIQUEMENT dans ces fichiers :
# exec.py (allow-list), updates.py, apt.py, nft.py, wireguard.py, backup.py.
BAD=$(grep -rln "subprocess" --include="*.py" backend agent 2>/dev/null | grep -v __pycache__ | grep -v "/tests/" | grep -v "backend/app/core/infraos/exec.py" | grep -v "backend/app/core/infraos/updates.py" | grep -v "backend/app/core/infraos/apt.py" | grep -v "backend/app/core/infraos/nft.py" | grep -v "backend/app/core/infraos/wireguard.py" | grep -v "backend/app/core/infraos/backup.py" || true)
if [ -n "$BAD" ]; then echo "KO: subprocess hors zone:"; echo "$BAD"; FAIL=1
else echo "OK: subprocess confine"; fi
exit $FAIL
