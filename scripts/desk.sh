#!/usr/bin/env bash
# Founder one-command day. PAPER only. No live orders. NO_PROMOTE.
#
#   ./scripts/desk.sh morning     # start API + website + dual-tape (09:00 IST)
#   ./scripts/desk.sh close       # after 15:30: stop capture, keep website, honesty + nightly
#   ./scripts/desk.sh website     # API + website only (no data capture)
#   ./scripts/desk.sh status      # pids / URLs / where to read reports
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv/bin/python"
VITE="$ROOT/apps/web/node_modules/.bin/vite"
RECON="$ROOT/data/recon"
mkdir -p "$RECON"
CMD="${1:-status}"

kill_port() {
  local port="$1"
  local pids
  pids=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    kill $pids 2>/dev/null || true
    sleep 1
    pids=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
      kill -9 $pids 2>/dev/null || true
    fi
  fi
}

stop_dual_tape() {
  touch "$RECON/paper_dual_tape_STOPPED.flag"
  for _ in 1 2 3 4 5 6; do
    if ! pgrep -f 'trading_agents_india dual-tape' >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  pkill -f 'trading_agents_india dual-tape' 2>/dev/null || true
  screen -S dual-tape-live-5s -X quit 2>/dev/null || true
  screen -S dual-tape-live-2s -X quit 2>/dev/null || true
  rm -f "$RECON/paper_dual_tape_RUNNING.flag"
}

ensure_api_web() {
  if ! lsof -tiTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
    screen -S api-server -X quit 2>/dev/null || true
    screen -dmS api-server zsh -lc "cd '$ROOT' && PYTHONPATH=apps/api/src '$PY' -m uvicorn api.main:app --app-dir apps/api/src --host 127.0.0.1 --port 8000 >> '$RECON/api-server.log' 2>&1"
  fi
  if ! lsof -tiTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
    screen -S web-dev -X quit 2>/dev/null || true
    screen -dmS web-dev zsh -lc "cd '$ROOT/apps/web' && '$VITE' --host 127.0.0.1 --port 5173 >> '$RECON/web-dev.log' 2>&1"
  fi
  sleep 4
}

write_status() {
  local extra="${1:-}"
  local API_PID WEB_PID DT_PID
  API_PID=$(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null | head -1 || true)
  WEB_PID=$(lsof -tiTCP:5173 -sTCP:LISTEN 2>/dev/null | head -1 || true)
  DT_PID=""
  if [[ -f "$RECON/paper_dual_tape_RUNNING.flag" ]]; then
    DT_PID=$("$PY" -c "import json; print(json.load(open('$RECON/paper_dual_tape_RUNNING.flag')).get('pid') or '')" 2>/dev/null || true)
  fi
  cat > "$RECON/paper_stack_status.json" <<EOF
{
  "ok": true,
  "as_of_ist_note": "scripts/desk.sh ${CMD}${extra}",
  "api": {"host": "127.0.0.1", "port": 8000, "pid": ${API_PID:-null}, "health": "http://127.0.0.1:8000/health"},
  "web": {"host": "127.0.0.1", "port": 5173, "pid": ${WEB_PID:-null}, "url": "http://127.0.0.1:5173/desk", "founder": "http://127.0.0.1:5173/pm"},
  "dual_tape": {"pid": ${DT_PID:-null}, "tick_seconds": 2, "stop": "touch data/recon/paper_dual_tape_STOPPED.flag"},
  "honesty_exam": {
    "ui": "http://127.0.0.1:5173/pm  →  Honesty exam (06)",
    "api": "http://127.0.0.1:8000/paper/sod-exam",
    "json": "data/recon/sod_exam_report.json",
    "ticket": "teams/06_backtesting/docs/BACKTEST_SOD_EXAM.md"
  },
  "nightly": {
    "cli": "python -m jobs post-market",
    "json": "data/recon/YYYY-MM-DD.json",
    "phd": "teams/02_phd_math/docs/handoffs/NIGHTLY_YYYY-MM-DD.md",
    "auditor": "teams/00_orchestrator/docs/AUDIT_LATEST.md"
  },
  "orders": "REFUSED",
  "promote": false
}
EOF
}

exam_days() {
  "$PY" - <<'PY'
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
d = datetime.now(ZoneInfo("Asia/Kolkata")).date()
days = []
while len(days) < 5:
    if d.weekday() < 5:
        days.append(d.isoformat())
    d -= timedelta(days=1)
print(",".join(reversed(days)))
PY
}

case "$CMD" in
  morning|start)
    # Cold start for 09:00 IST. Kills stale listeners, then brings the full paper desk up.
    pkill -f 'trading_agents_india dual-tape' 2>/dev/null || true
    kill_port 8000
    kill_port 5173
    screen -S api-server -X quit 2>/dev/null || true
    screen -S web-dev -X quit 2>/dev/null || true
    screen -S dual-tape-live-5s -X quit 2>/dev/null || true
    screen -S dual-tape-live-2s -X quit 2>/dev/null || true
    screen -wipe >/dev/null 2>&1 || true
    rm -f "$RECON/paper_dual_tape_STOPPED.flag"
    PYTHONPATH="$ROOT/packages/desk-intel/src${PYTHONPATH:+:$PYTHONPATH}" \
      "$PY" -m jobs pre-market --offline >> "$RECON/pre_market.log" 2>&1 || true
    "$PY" -m desk_ml fix-first >> "$RECON/fix_first.log" 2>&1 || true
    screen -dmS api-server zsh -lc "cd '$ROOT' && PYTHONPATH=apps/api/src '$PY' -m uvicorn api.main:app --app-dir apps/api/src --host 127.0.0.1 --port 8000 >> '$RECON/api-server.log' 2>&1"
    screen -dmS web-dev zsh -lc "cd '$ROOT/apps/web' && '$VITE' --host 127.0.0.1 --port 5173 >> '$RECON/web-dev.log' 2>&1"
    screen -dmS dual-tape-live-2s zsh -lc "cd '$ROOT' && '$PY' -u -m trading_agents_india dual-tape --live-chain --paper-train --paper-scalp --tick-seconds 2 --max-ticks 0 >> '$RECON/dual_tape_live_2s.log' 2>&1"
    sleep 6
    write_status
    echo "MORNING UP. Desk http://127.0.0.1:5173/desk  Founder http://127.0.0.1:5173/pm"
    echo "On /pm: pick index then START TRADE. PAPER. No live orders."
    screen -ls || true
    ;;
  close|night|nightly)
    echo "CLOSE: stop data capture, keep website, honesty exam + nightly."
    stop_dual_tape
    ensure_api_web
    DAYS="$(exam_days)"
    echo "Nightly first so exam can read session_kind. Then honesty exam."
    PYTHONPATH="$ROOT/packages/desk-intel/src${PYTHONPATH:+:$PYTHONPATH}" \
      "$PY" -m jobs post-market | tee "$RECON/post_market_last.stdout.json"
    echo "Honesty exam days: $DAYS"
    "$PY" -m desk_ml sod-exam --days "$DAYS" --underlyings NIFTY | tee "$RECON/sod_exam_last.stdout.json"
    DAY="$("$PY" -c "from zoneinfo import ZoneInfo; from datetime import datetime; print(datetime.now(ZoneInfo('Asia/Kolkata')).date())")"
    cat > "$RECON/close_status.txt" <<EOF
Closed IST day ${DAY}
Website ON: http://127.0.0.1:5173/desk
Honesty UI: http://127.0.0.1:5173/pm  (Honesty exam)
Honesty JSON: data/recon/sod_exam_report.json
Nightly JSON: data/recon/${DAY}.json
Nightly PhD:  teams/02_phd_math/docs/handoffs/NIGHTLY_${DAY}.md
Auditor:      teams/00_orchestrator/docs/AUDIT_LATEST.md
Capture: STOPPED
EOF
    write_status " close ${DAY}"
    cat "$RECON/close_status.txt"
    ;;
  website)
    stop_dual_tape
    ensure_api_web
    write_status " website-only"
    echo "Website ON. Capture OFF. http://127.0.0.1:5173/desk"
    ;;
  status)
    write_status
    echo "=== desk status ==="
    echo "API  : $(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null | head -1 || echo DOWN)  http://127.0.0.1:8000/health"
    echo "WEB  : $(lsof -tiTCP:5173 -sTCP:LISTEN 2>/dev/null | head -1 || echo DOWN)  http://127.0.0.1:5173/desk"
    echo "TAPE : $(pgrep -f 'trading_agents_india dual-tape' | head -1 || echo STOPPED)"
    echo "Honesty: http://127.0.0.1:5173/pm  and  data/recon/sod_exam_report.json"
    echo "Nightly: data/recon/\$(IST-date).json  and  teams/02_phd_math/docs/handoffs/NIGHTLY_*.md"
    if [[ -f "$RECON/close_status.txt" ]]; then
      echo "--- last close ---"
      cat "$RECON/close_status.txt"
    fi
    ;;
  watch-close)
    echo "Waiting until 15:40 IST then running close..."
    "$PY" - <<'PY'
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
ist = ZoneInfo("Asia/Kolkata")
now = datetime.now(ist)
target = now.replace(hour=15, minute=40, second=0, microsecond=0)
if now >= target:
    print(f"already past 15:40 IST ({now.isoformat()}); close should be run now")
else:
    print(f"sleep until {target.isoformat()} ({int((target-now).total_seconds())}s)")
    while datetime.now(ist) < target:
        time.sleep(20)
print("watch-close reached 15:40 IST")
PY
    exec "$0" close
    ;;
  *)
    echo "usage: $0 morning|close|website|status|watch-close" >&2
    exit 2
    ;;
esac
