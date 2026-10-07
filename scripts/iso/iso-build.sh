#!/bin/bash
# Lance le build ISO sur le builder dedie (VM Debian 13, jamais le LXC dev).
# Usage: bash scripts/iso/iso-build.sh
set -euo pipefail
bash "$(dirname "$0")/../../iso/build.sh"
