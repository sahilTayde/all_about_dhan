#!/usr/bin/env bash
# PAPER stack: API :8000, Vite :5173, dual-tape (5s). No live orders.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv/bin/python"
VITE="$ROOT/apps/web/node_modules/.bin/vite"
RECON="$ROOT/data/recon"
mkdir -p "$RECON"

kill_port() {
  local port="$1"
  local pids
  pids=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    kill -9 $pids 2>/dev/null || true
  fi
}

pkill -f 'trading_agents_india dual-tape' 2>/dev/null || true
kill_port 8000
kill_port 5173
screen -S api-server -X quit 2>/dev/null || true
screen -S web-dev -X quit 2>/dev/null || true
screen -S dual-tape-live-5s -X quit 2>/dev/null || true
screen -wipe >/dev/null 2>&1 || true
rm -f "$RECON/paper_dual_tape_STOPPED.flag"
sleep 1

screen -dmS api-server zsh -lc "cd '$ROOT' && PYTHONPATH=apps/api/src '$PY' -m uvicorn api.main:app --app-dir apps/api/src --host 127.0.0.1 --port 8000 >> '$RECON/api-server.log' 2>&1"
screen -dmS web-dev zsh -lc "cd '$ROOT/apps/web' && '$VITE' --host 127.0.0.1 --port 5173 >> '$RECON/web-dev.log' 2>&1"
screen -dmS dual-tape-live-5s zsh -lc "cd '$ROOT' && '$PY' -u -m trading_agents_india dual-tape --live-chain --paper-train --paper-scalp --tick-seconds 5 --max-ticks 0 >> '$RECON/dual_tape_live_5s.log' 2>&1"

sleep 6
API_PID=$(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null | head -1)
WEB_PID=$(lsof -tiTCP:5173 -sTCP:LISTEN 2>/dev/null | head -1)
DT_PID=""
if [[ -f "$RECON/paper_dual_tape_RUNNING.flag" ]]; then
  DT_PID=$("$PY" -c "import json; print(json.load(open('$RECON/paper_dual_tape_RUNNING.flag'))['pid'])")
fi

cat > "$RECON/paper_stack_status.json" <<EOF
{
  "ok": true,
  "as_of_ist_note": "written by scripts/restart_paper_stack.sh",
  "api": {"host": "127.0.0.1", "port": 8000, "pid": ${API_PID:-null}, "health": "http://127.0.0.1:8000/health"},
  "web": {"host": "127.0.0.1", "port": 5173, "pid": ${WEB_PID:-null}, "url": "http://127.0.0.1:5173/", "proxy_paper": "http://127.0.0.1:5173/paper/ml-books"},
  "dual_tape": {"pid": ${DT_PID:-null}, "tick_seconds": 5, "flags": ["--live-chain", "--paper-train", "--paper-scalp"], "stop": "touch data/recon/paper_dual_tape_STOPPED.flag"},
  "orders": "REFUSED",
  "promote": false
}
EOF

echo "API pid=${API_PID:-DOWN} WEB pid=${WEB_PID:-DOWN} DUAL-TAPE pid=${DT_PID:-pending}"
screen -ls || true
