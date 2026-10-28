#!/usr/bin/env bash
# Daily recorder start / post-market close, run by Claude scheduled tasks (launchd is blocked by macOS
# privacy for ~/Documents, see data/recon/autostart_launchd.log). PAPER, record-only. No orders.
#   scripts/claude_daily.sh morning   # waits (detached) until 08:25 IST, then restarts v2 + cross recorders; also queues close
#   scripts/claude_daily.sh close     # waits (detached) until 15:31 IST, then ./scripts/desk.sh close + FIN1 shadow log
#                                     # (Fridays: weekly FIN1 report -> data/recon/fin1_shadow_week.txt, shown on Mondays)
#   scripts/claude_daily.sh status    # today's log + recorder health
#   scripts/claude_daily.sh heal      # 09:00-15:25 IST on trading days: start the v2 / cross recorder only if it is down
#                                     # (the morning waiter runs it every 10 min after the 08:25 start)
#   scripts/claude_daily.sh report    # end-of-day report -> data/recon/daily_report_<day>.txt (tape, FIN1/S2, honesty)
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
MORNING='if [[ "$(TZ=Asia/Kolkata date +%H%M)" > 0830 ]]; then ./scripts/desk.sh recorder-start || true; ./scripts/desk.sh cross-start || true; else ./scripts/desk.sh recorder-stop; ./scripts/desk.sh recorder-start; ./scripts/desk.sh cross-stop; ./scripts/desk.sh cross-start; fi; sleep 90; ./scripts/desk.sh recorder-status; for _ in $(seq 1 45); do sleep 600; ./scripts/claude_daily.sh heal; done'

# FIN1 is shadow-only (paper log from the tape, never an order): scripts/lab5y/fin1_shadow.py
CLOSE='./scripts/desk.sh close; .venv/bin/python scripts/lab5y/fin1_shadow.py day; if [[ "$(TZ=Asia/Kolkata date +%u)" == 5 ]]; then .venv/bin/python scripts/lab5y/fin1_shadow.py week 5 > data/recon/fin1_shadow_week.txt; fi; ./scripts/claude_daily.sh report'

case "${1:-}" in
  morning) later morning 08:25 "$MORNING"; later close 15:31 "$CLOSE" ;;  # close too: the close task can stall on an approval prompt
  close)   [[ "$(TZ=Asia/Kolkata date +%u)" == 1 && -f data/recon/fin1_shadow_week.txt ]] && cat data/recon/fin1_shadow_week.txt
           later close 15:31 "$CLOSE" ;;
  status)  tail -20 "$LOG" 2>/dev/null; ./scripts/desk.sh recorder-status 2>&1 | tail -4 ;;
  heal)    # self-heal during market hours; never stops a running recorder (recorder-start / cross-start skip a live one)
           wait_s 09:00 >/dev/null || { echo "not a trading day ($DAY)"; exit 0; }
           hm="$(TZ=Asia/Kolkata date +%H%M)"; [[ "$hm" < 0900 || "$hm" > 1525 ]] && { echo "outside 09:00-15:25 IST ($hm)"; exit 0; }
           h="$(./scripts/desk.sh recorder-status 2>&1 | grep -i 'health:')"; c="$(pgrep -f 'python.*-m marketdata.cross_market' >/dev/null && echo up || echo down)"
           if [[ "$h" == *HEALTHY* && "$c" == up ]]; then echo "healthy: $h; cross $c"
           else echo "=== $(date) heal: '$h' cross=$c -> start what is down" | tee -a "$LOG"
                ./scripts/desk.sh recorder-start 2>&1 | tee -a "$LOG" | tail -2; ./scripts/desk.sh cross-start 2>&1 | tee -a "$LOG" | tail -2
           fi ;;
  report)  R="data/recon/daily_report_${DAY}.txt"; T="data/tape/v2/$DAY"
           { echo "Daily report $DAY (paper only, no orders)"
             if [[ -f "$T/recorder.log" ]]; then
               ist() { "$PY" -c "import sys;from datetime import datetime;from zoneinfo import ZoneInfo;print(datetime.strptime(sys.argv[1][:19],'%Y-%m-%d %H:%M:%S').astimezone(ZoneInfo('Asia/Kolkata')).strftime('%H:%M'))" "$1"; }
               echo "Tape: $(ist "$(head -1 "$T/recorder.log")")-$(ist "$(tail -1 "$T/recorder.log")") IST, depth $(du -h "$T/depth_quotes.jsonl" 2>/dev/null | cut -f1)"
             else echo "Tape: none for $DAY"; fi
             grep -h "^FIN1 $DAY" "$LOG" 2>/dev/null || echo "FIN1/S2: no row yet (the close step logs it at 15:31 IST)"
             "$PY" scripts/lab5y/fin1_shadow.py week 5 | grep "since start"
             "$PY" scripts/lab5y/fin1_shadow.py forward "$DAY" | grep -E "^FWD|calibration" || echo "Forward view: no row"
             "$PY" -c "import json;r=json.load(open('data/recon/sod_exam_report.json'));d=[x for x in r['days'] if x['day']=='$DAY'];print('Paper desk honesty:',r.get('overall_honesty'),'| today:',(d[0].get('honesty') if d else 'no row'));[print(' ',s) for s in r.get('stories',[]) if s.startswith('$DAY')]" 2>/dev/null || echo "Paper desk honesty: no report"
             grep -h "heal:" "$LOG" 2>/dev/null | sed 's/^/Self-heal: /'
           } > "$R"; cat "$R" ;;
  *) echo "usage: $0 morning|close|status|heal|report" >&2; exit 1 ;;
esac
