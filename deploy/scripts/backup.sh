#!/usr/bin/env bash
# Snapshot state (output_hash) then restic if RESTIC_REPOSITORY is set.
# Paper only. Timeout from runtime.jobs.JOBS["backup"] = 300s.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
STATE="${AAD_STATE_DIR:-$ROOT/data/state}"
DEST="${1:-$ROOT/var/backup/latest}"
export AAD_STATE_DIR="$STATE"
timeout 300 python -m runtime backup --state-dir "$STATE" --snapshot "$DEST"
if [[ -n "${RESTIC_REPOSITORY:-}" ]]; then
  # Host supplies RESTIC_REPOSITORY / RESTIC_PASSWORD via the environment — never committed.
  timeout 300 restic backup --quiet "$DEST"
fi
