#!/usr/bin/env bash
# Nightly paper warehouse ETL (read-only on sources; writes data/warehouse/analytics.sqlite).
# Paper only. No broker calls, no credentials. Safe to re-run: unchanged files are skipped.
#
# cron (server clock in IST), after the close, Mon-Fri:
#   35 16 * * 1-5  /path/to/all_about_dhan/scripts/nightly_warehouse_etl.sh
# cron (server clock in UTC): 16:35 IST = 11:05 UTC
#   5 11 * * 1-5   /path/to/all_about_dhan/scripts/nightly_warehouse_etl.sh
#
# Args go to `python -m warehouse.etl`: `[--root DIR] [--db FILE] run [--full]` (or `status`, `query ...`).
# If no subcommand is given, `run` is appended: `--root /data/aad` = `--root /data/aad run`.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
export PYTHONPATH="$REPO_ROOT/packages/warehouse/src${PYTHONPATH:+:$PYTHONPATH}"

LOG_DIR="$REPO_ROOT/data/warehouse"
mkdir -p "$LOG_DIR"
# One run at a time; a second cron fire while the first is still going exits quietly.
exec 9>"$LOG_DIR/etl.lock"
if ! flock -n 9; then
  echo "$(date -Is) warehouse ETL already running; skipped" >>"$LOG_DIR/etl.log"
  exit 0
fi

case " $* " in
  *" run "* | *" status "* | *" query "*) ;;
  *) set -- "$@" run ;;
esac
echo "$(date -Is) warehouse ETL start: $*" >>"$LOG_DIR/etl.log"
status=0
"$PY" -m warehouse.etl "$@" >>"$LOG_DIR/etl.log" 2>&1 || status=$?
echo "$(date -Is) warehouse ETL exit $status" >>"$LOG_DIR/etl.log"
exit "$status"
