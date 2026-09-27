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
LOG_DIR="$REPO_ROOT/data/premarket"
mkdir -p "$LOG_DIR"

# The project environment has PyYAML; a bare system python3 usually does not.
if [ -x .venv/bin/python ]; then
  RUN=(.venv/bin/python)
elif command -v uv >/dev/null 2>&1; then
  RUN=(uv run --project "$REPO_ROOT" --with pyyaml python)
else
  echo "$(date -Is) premarket: no project venv (.venv) and no uv; run .cursor/install.sh first" | tee -a "$LOG_DIR/premarket.log" >&2
  exit 2
fi
if ! "${RUN[@]}" -c 'import yaml' >/dev/null 2>&1; then
  echo "$(date -Is) premarket: PyYAML missing in ${RUN[*]}; run .cursor/install.sh" | tee -a "$LOG_DIR/premarket.log" >&2
  exit 2
fi
export PYTHONPATH="$REPO_ROOT/packages/premarket/src${PYTHONPATH:+:$PYTHONPATH}"

status=0
"${RUN[@]}" -m premarket --print none "$@" >>"$LOG_DIR/premarket.log" 2>&1 || status=$?
echo "$(date -Is) premarket exit $status" >>"$LOG_DIR/premarket.log"
exit "$status"
