#!/usr/bin/env bash
# Restore a snapshot and require the stored output_hash to match.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
STATE="${AAD_STATE_DIR:-$ROOT/data/state}"
SNAP="${1:-}"
if [[ -z "$SNAP" ]]; then
  echo "usage: restore.sh <snapshot-dir>" >&2
  exit 2
fi
if [[ -n "${RESTIC_REPOSITORY:-}" && ! -d "$SNAP" ]]; then
  timeout 300 restic restore latest --target "$SNAP"
fi
timeout 300 python -m runtime restore --state-dir "$STATE" --snapshot "$SNAP"
