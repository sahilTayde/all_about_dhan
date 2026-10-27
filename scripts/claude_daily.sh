#!/usr/bin/env bash
# Daily recorder start / post-market close, run by Claude scheduled tasks (launchd is blocked by macOS
# privacy for ~/Documents, see data/recon/autostart_launchd.log). PAPER, record-only. No orders.
#   scripts/claude_daily.sh morning   # waits (detached) until 08:25 IST, then restarts v2 + cross recorders
#   scripts/claude_daily.sh close     # waits (detached) until 15:31 IST, then ./scripts/desk.sh close + FIN1 shadow log
#                                     # (Fridays: weekly FIN1 report -> data/recon/fin1_shadow_week.txt, shown on Mondays)
#   scripts/claude_daily.sh status    # today's log + recorder health
# The wait is computed in IST, so the US DST change (Nov 1) cannot shift the IST time.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT" || exit 1
PY="$ROOT/.venv/bin/python"
DAY="$("$PY" -c "from zoneinfo import ZoneInfo; from datetime import datetime; print(datetime.now(ZoneInfo('Asia/Kolkata')).date())")"
LOG="data/recon/claude_daily_${DAY}.log"; mkdir -p data/recon

# seconds until HH:MM IST today; exit 2 if not a trading day (weekend / NSE holiday file used by desk_autostart.sh)
wait_s() {
  "$PY" - "$1" "$DAY" <<'PY'
import sys, glob, pathlib
from datetime import datetime, date
from zoneinfo import ZoneInfo
hh, mm = map(int, sys.argv[1].split(":")); d = date.fromisoformat(sys.argv[2]); hol = set()
for f in glob.glob(str(pathlib.Path.home() / "paper_extra_rt/dhan/research/lab/lib/nse_holidays_20*.csv")):
    hol |= {l[:10] for l in open(f) if l[:2] == "20"}
if d.weekday() >= 5 or d.isoformat() in hol:
    sys.exit(2)
now = datetime.now(ZoneInfo("Asia/Kolkata"))
print(max(0, int((now.replace(hour=hh, minute=mm, second=0, microsecond=0) - now).total_seconds())))
PY
}

later() {  # later NAME HH:MM "cmd": detach so the scheduled Claude run can finish while we wait
  local q="data/recon/claude_daily_${DAY}.$1.pid" s
  if [[ -f "$q" ]] && kill -0 "$(cat "$q")" 2>/dev/null; then  # Run now + cron the same day: one waiter only
    echo "$1 already queued for $DAY (pid $(cat "$q")). log=$LOG"; return 0
  fi
  s="$(wait_s "$2")" || { echo "$(date) $DAY not a trading day: skip $1" >> "$LOG"; echo "not a trading day ($DAY)"; return 0; }
  nohup bash -c "sleep $s; echo \"=== \$(date) $1\"; $3" >> "$LOG" 2>&1 &
  echo $! > "$q"
  echo "scheduled $1 in ${s}s (at $2 IST, day $DAY). log=$LOG"
}

# Restart for the new day (so the 09:08 pre-open is taped). Run late (after 08:25) it never stops a running
# recorder mid-session: it only starts one that is down.
MORNING='if [[ "$(TZ=Asia/Kolkata date +%H%M)" > 0830 ]]; then ./scripts/desk.sh recorder-start || true; ./scripts/desk.sh cross-start || true; else ./scripts/desk.sh recorder-stop; ./scripts/desk.sh recorder-start; ./scripts/desk.sh cross-stop; ./scripts/desk.sh cross-start; fi; sleep 90; ./scripts/desk.sh recorder-status'

# FIN1 is shadow-only (paper log from the tape, never an order): scripts/lab5y/fin1_shadow.py
CLOSE='./scripts/desk.sh close; .venv/bin/python scripts/lab5y/fin1_shadow.py day; if [[ "$(TZ=Asia/Kolkata date +%u)" == 5 ]]; then .venv/bin/python scripts/lab5y/fin1_shadow.py week 5 > data/recon/fin1_shadow_week.txt; fi'

case "${1:-}" in
  morning) later morning 08:25 "$MORNING" ;;
  close)   [[ "$(TZ=Asia/Kolkata date +%u)" == 1 && -f data/recon/fin1_shadow_week.txt ]] && cat data/recon/fin1_shadow_week.txt
           later close 15:31 "$CLOSE" ;;
  status)  tail -20 "$LOG" 2>/dev/null; ./scripts/desk.sh recorder-status 2>&1 | tail -4 ;;
  *) echo "usage: $0 morning|close|status" >&2; exit 1 ;;
esac
