#!/usr/bin/env bash
# Grant Nivaro platform-staff (admin) access to an existing account, locally.
#   scripts/make-admin.sh you@example.com
# The account must exist (register on the website first). Admin API calls also need a session signed
# in with two-step verification: turn it on in Settings → Security, then sign out and back in.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[[ $# -eq 1 ]] || { echo "usage: scripts/make-admin.sh <email>" >&2; exit 2; }
cd "$ROOT/apps/backend"
uv run python -m app.cli make-staff "$1" && echo "✓ $1 is now platform staff (audited as admin.staff_granted)"
