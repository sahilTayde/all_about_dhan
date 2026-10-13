#!/usr/bin/env bash
# Unattended weekday start of the PAPER desk (2026-10-13, Sahil OK). Started by launchd
# (~/Library/LaunchAgents/com.allaboutdhan.desk-autostart.plist) at 21:00 Mac local time (US Central) Sun-Thu,
# i.e. 07:30 IST (CDT) / 08:30 IST (CST). It waits until 08:30 IST. Never mints or prints a token, never places an order,
# never pushes. Steps never wait on the slow pre-market jobs (desk.sh morning runs those in screen desk-slow).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT" || exit 1
PY="$ROOT/.venv/bin/python"
DRY="${DESK_AUTOSTART_DRY:-0}"   # 1 = print the steps only (no waiting, nothing started or stopped)
run() { if [[ "$DRY" == "1" ]]; then echo "DRY: $*"; else "$@"; fi; }
DAY="${DESK_AUTOSTART_DAY:-}"
[[ -n "$DAY" ]] || DAY="$("$PY" -c "from zoneinfo import ZoneInfo; from datetime import datetime; print(datetime.now(ZoneInfo('Asia/Kolkata')).date())")"
mkdir -p data/recon; LOG="data/recon/autostart_${DAY}.log"
[[ "$DRY" == "1" ]] || exec >> "$LOG" 2>&1
echo "=== autostart $(date) IST day $DAY ==="
"$PY" - "$DAY" "$DRY" <<'PY' || { echo "not a trading day: exit"; exit 0; }
import sys, glob, time
from datetime import datetime, date
from zoneinfo import ZoneInfo
d = date.fromisoformat(sys.argv[1]); hol = set()
for f in glob.glob(str(__import__("pathlib").Path.home() / "paper_extra_rt/dhan/research/lab/lib/nse_holidays_20*.csv")):
    hol |= {l[:10] for l in open(f) if l[:2] == "20"}
if d.weekday() >= 5 or d.isoformat() in hol:
    sys.exit(1)
ist = ZoneInfo("Asia/Kolkata"); t = datetime.now(ist).replace(hour=8, minute=30, second=0, microsecond=0)
if sys.argv[2] == "1":
    sys.exit(0)
if datetime.now(ist) > t.replace(hour=15, minute=0):
    sys.exit(1)
w = (t - datetime.now(ist)).total_seconds()
if w > 0:
    print(f"waiting {int(w)}s until 08:30 IST", flush=True); time.sleep(w)
PY
echo "--- $(date) recorders (v2 restarted for the new day so it records the 09:08-09:15 pre-open)"
run ./scripts/desk.sh recorder-stop || true
run ./scripts/desk.sh recorder-start || echo "WARN recorder-start failed"
screen -ls | grep -q "\.cross-recorder" || run ./scripts/desk.sh cross-start || echo "WARN cross-start failed"
echo "--- $(date) desk morning (API, website, dual-tape armed; slow jobs in screen desk-slow)"
export MARKET_READ_LOG=1
run ./scripts/desk.sh morning || echo "WARN morning returned $?"
echo "--- $(date) v2 shadow"
run ./scripts/desk.sh shadow-stop || true
run ./scripts/desk.sh shadow-start || echo "WARN shadow-start failed"
echo "--- $(date) paper-extra (PX strategies + Q01 v1.1 desk + Q01_T15 shadow)"
run screen -S paper-extra -X quit 2>/dev/null || true
run pkill -f "scripts/paper_extra/runner.py loop" 2>/dev/null || true
run sleep 1
run screen -dmS paper-extra zsh -lc "cd '$ROOT' && caffeinate -dimsu env PYTHONPATH=packages/brokers/src '$PY' -u scripts/paper_extra/runner.py loop >> data/recon/paper_extra/runner.log 2>&1"
run sleep 20
echo "--- $(date) health"
screen -ls
curl -s -o /dev/null -w "api %{http_code}\n" http://127.0.0.1:8000/health
curl -s -o /dev/null -w "web %{http_code}\n" http://127.0.0.1:5173/desk
echo "=== autostart done $(date) ==="
