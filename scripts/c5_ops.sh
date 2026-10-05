#!/usr/bin/env bash
# C5-04 founder ops for a 5-customer paper night. Never live.
#
#   ./scripts/c5_ops.sh start [--with-founder] [--with-shadow] [--dry-run]
#   ./scripts/c5_ops.sh status
#   ./scripts/c5_ops.sh stop
#   ./scripts/c5_ops.sh backup [--snapshot PATH]
#   ./scripts/c5_ops.sh restore --dry-run --snapshot PATH
#
# Shared: python -m runtime signal --once
# Per enabled customer: python -m runtime exec --account <id> --once
# Cap: 5 customer execs. Founder + v2-shadow are opt-in flags.
# Does not write data/recon or data/shadow (legacy dual-tape / shadow books).
set -euo pipefail
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${AAD_ROOT:-$(cd "$_SCRIPT_DIR/.." && pwd)}"
cd "$ROOT"
PY="${AAD_C5_PY:-${AAD_V2_PY:-$ROOT/.venv-v2/bin/python}}"
CMD="${1:-status}"
if [[ $# -gt 0 ]]; then
  shift
fi

refuse_live() {
  echo '{"ok":false,"reason":"V2 c5 fail-closed: mode is live and cannot start","orders":"REFUSED","live_broker":false}' >&2
  exit 2
}

# Fail closed on live before any python / venv check. Never enable live.
prev=""
for arg in "$@"; do
  low="$(printf '%s' "$arg" | tr '[:upper:]' '[:lower:]')"
  if [[ "$prev" == "--mode" ]]; then
    case "$low" in
      live|limited_live|limited-live|dhan) refuse_live ;;
    esac
  fi
  case "$low" in
    --mode=live|--mode=limited_live|--mode=limited-live|--mode=dhan) refuse_live ;;
  esac
  prev="$low"
done
env_mode="$(printf '%s' "${AAD_C5_MODE:-}" | tr '[:upper:]' '[:lower:]')"
case "$env_mode" in
  live|limited_live|limited-live|dhan) refuse_live ;;
esac

case "$CMD" in
  start|status|stop|backup|restore|plan|c5-start|c5-status|c5-stop|c5-backup|c5-restore|c5-plan)
    CMD="${CMD#c5-}"
    ;;
  -h|--help|help)
    echo "usage: $0 start|status|stop|backup|restore|plan  (paper/shadow only; never live)"
    exit 0
    ;;
  *)
    echo "usage: $0 start|status|stop|backup|restore|plan  (paper/shadow only; never live)" >&2
    exit 2
    ;;
esac

if [[ ! -x "$PY" ]]; then
  echo "ERROR: C5 python missing at $PY. Set AAD_C5_PY or run ./scripts/mac_setup_v2.sh (does not touch legacy .venv)." >&2
  exit 2
fi

exec "$PY" -m accounts "c5-${CMD}" "$@"
