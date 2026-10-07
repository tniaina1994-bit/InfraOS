#!/bin/bash
# Build frontend prod (frontend/dist, servi par nginx).
set -euo pipefail
cd "$(dirname "$0")/../../frontend"
npm run build
echo "dist/ pret pour /usr/share/infraos/ui"
