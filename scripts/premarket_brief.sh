#!/usr/bin/env bash
# Pre-market brief (advisory only): writes data/premarket/india_index_<date>.{json,md}.
# Never places orders, needs no credentials, and the paper engine does not wait for it.
# Always exits 0 unless the config is broken: a missing source is recorded in the output instead.
#
# cron (server clock in IST), Mon-Fri before 09:00:
#   30 8 * * 1-5  /path/to/all_about_dhan/scripts/premarket_brief.sh
# cron (server clock in UTC): 08:30 IST = 03:00 UTC
#   0 3 * * 1-5   /path/to/all_about_dhan/scripts/premarket_brief.sh
#
# Extra args go to `python -m premarket`, e.g. `--offline` or `--market india_index`.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
export PYTHONPATH="$REPO_ROOT/packages/premarket/src${PYTHONPATH:+:$PYTHONPATH}"

LOG_DIR="$REPO_ROOT/data/premarket"
mkdir -p "$LOG_DIR"
status=0
"$PY" -m premarket --print none "$@" >>"$LOG_DIR/premarket.log" 2>&1 || status=$?
echo "$(date -Is) premarket exit $status" >>"$LOG_DIR/premarket.log"
exit "$status"
