#!/usr/bin/env bash
# deploy.sh <sha> [--emergency]
# Refuse 09:00–15:35 IST unless --emergency. Backup, migrate, wait READY, else rollback.
# Clock: AAD_NOW (ISO +05:30) for tests. No credentials. Paper only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
SHA="${1:-}"
shift || true
if [[ -z "$SHA" || "$SHA" == --* ]]; then
  echo "usage: deploy.sh <sha> [--emergency]" >&2
  exit 2
fi
STATE="${AAD_STATE_DIR:-$ROOT/data/state}"
export AAD_STATE_DIR="$STATE"
ARGS=(--sha "$SHA" --state-dir "$STATE")
for a in "$@"; do ARGS+=("$a"); done
if [[ -n "${AAD_NOW:-}" ]]; then ARGS+=(--now "$AAD_NOW"); fi
exec python -m runtime deploy "${ARGS[@]}"
