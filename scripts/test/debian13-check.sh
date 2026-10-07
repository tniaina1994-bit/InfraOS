#!/bin/bash
# Compat Debian 13: manifests valides, paquets trixie connus, control present.
set -u
FAIL=0
echo "== manifests =="
for m in modules/*/manifest.yaml; do
  python3 -c "import yaml,sys; d=yaml.safe_load(open('$m')); assert 'name' in d and 'packages' in d, 'manifest incomplet'" 2>/dev/null \
  || { echo "KO: $m"; FAIL=1; }
done
[ $FAIL -eq 0 ] && echo "OK: $(ls modules/*/manifest.yaml | wc -l) manifests"
echo "== paquets Debian 13 connus (spot-check) =="
for p in bind9 kea-dhcp4-server nftables wireguard samba restic nginx unattended-upgrades; do
  grep -q "^${p}$" iso/packages.list && echo "OK $p" || { echo "KO $p absent de packages.list"; FAIL=1; }
done
echo "== packaging =="
[ -f packaging/debian/control ] && echo "OK packaging/debian/control" || { echo "KO packaging/debian/control"; FAIL=1; }
[ -f LICENSE ] && echo "OK LICENSE" || { echo "KO LICENSE"; FAIL=1; }
[ -f backend/pyproject.toml ] && echo "OK backend/pyproject.toml" || { echo "KO backend"; FAIL=1; }
[ -f frontend/package.json ] && echo "OK frontend/package.json" || { echo "KO frontend"; FAIL=1; }
exit $FAIL
