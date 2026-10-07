#!/bin/bash
# Fumee e2e contre le LXC dev (lecture + login, sans mutation).
# Usage: bash tests/e2e-api.sh [http://192.168.10.39:8000]
set -u
API="${1:-http://192.168.10.39:8000}"
fail() { echo "KO: $1"; exit 1; }
curl -s --max-time 5 "$API/api/health" | grep -q '"status":"ok"' || fail "health"
curl -s --max-time 5 "$API/api/v1/health" | grep -q '"status":"ok"' || fail "v1/health"
curl -s --max-time 5 "$API/docs" | grep -qi "swagger" || fail "docs"
curl -s --max-time 5 "$API/openapi.json" | grep -q '"openapi"' || fail "openapi"
echo "E2E OK ($API)"
