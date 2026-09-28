#!/usr/bin/env bash
# Founder one-command day. PAPER only. No live orders. NO_PROMOTE.
#
#   ./scripts/desk.sh preflight        # versions, imports, node, token file (no token printed)
#   ./scripts/desk.sh morning          # preflight + API + website + dual-tape (09:00 IST)
#   ./scripts/desk.sh website          # preflight + API + website only (no data capture)
#   ./scripts/desk.sh watch-open       # wait until 09:30 IST Mon–Fri, then dual-tape
#   ./scripts/desk.sh recorder-start   # v2 marketdata --record-only in .venv-v2 (screen v2-recorder)
#   ./scripts/desk.sh recorder-stop    # stop v2 recorder; leave tapes intact
#   ./scripts/desk.sh recorder-status  # process + last line of today's IST recorder.log
#   ./scripts/desk.sh v2-start         # ALL V2 paper services (recorder + runtime engine/health/gateway)
#   ./scripts/desk.sh v2-stop          # stop ALL V2 services; leave tapes + state files intact
#   ./scripts/desk.sh v2-status        # process + screen + last status line per V2 service
#   ./scripts/desk.sh start-all        # website + watch-open + v2-start (both stacks)
#   ./scripts/desk.sh stop-all         # same as close
#   ./scripts/desk.sh close            # after 15:30: stop capture + ALL V2, keep website, honesty + nightly
#   ./scripts/desk.sh status           # pids / URLs / where to read reports
#
set -euo pipefail
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${AAD_ROOT:-$(cd "$_SCRIPT_DIR/.." && pwd)}"
cd "$ROOT"
PY="${AAD_PY:-$ROOT/.venv/bin/python}"
V2_PY="${AAD_V2_PY:-$ROOT/.venv-v2/bin/python}"
VITE="$ROOT/apps/web/node_modules/.bin/vite"
RECON="${AAD_RECON:-$ROOT/data/recon}"
TAPE_V2="${AAD_TAPE_V2:-$ROOT/data/tape/v2}"
RECORDER_SCREEN="v2-recorder"
ENGINE_SCREEN="v2-engine"
HEALTH_SCREEN="v2-health"
GATEWAY_SCREEN="v2-gateway"
NODE_DIR="${NODE_DIR:-}"
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

rotate_log() {  # size-based, keep 7: the live log must not fill the disk
  local log="$1" max=$((50 * 1024 * 1024))
  [[ -f "$log" ]] || return 0
  local size
  size=$(wc -c <"$log" | tr -d ' ')
  (( size < max )) && return 0
  for n in 6 5 4 3 2 1; do [[ -f "$log.$n" ]] && mv -f "$log.$n" "$log.$((n + 1))"; done
  mv -f "$log" "$log.1"
}

health_supervise_available() {
  "$PY" -c "import health.supervise" >/dev/null 2>&1
}

dual_tape_child_cmd() {
  # Same args whether or not health.supervise wraps them.
  printf "%s" "'$PY' -u -m trading_agents_india dual-tape --live-chain --paper-train --paper-scalp --tick-seconds 2 --max-ticks 0"
}

dual_tape_launch_inner() {
  # Command that runs inside the dual-tape-live-2s screen (after cd ROOT).
  local child
  child="$(dual_tape_child_cmd)"
  if health_supervise_available; then
    printf "%s" "'$PY' -u -m health.supervise -- $child >> '$RECON/dual_tape_live_2s.log' 2>&1"
  else
    echo "WARNING: health.supervise is not importable with $PY; starting dual-tape without supervisor" >&2
    printf "%s" "$child >> '$RECON/dual_tape_live_2s.log' 2>&1"
  fi
}

start_dual_tape() {
  rm -f "$RECON/paper_dual_tape_STOPPED.flag"
  screen -S dual-tape-live-2s -X quit 2>/dev/null || true
  rotate_log "$RECON/dual_tape_live_2s.log"
  local inner
  inner="$(dual_tape_launch_inner)"
  screen -dmS dual-tape-live-2s zsh -lc "cd '$ROOT' && $inner"
}

arm_dual_tape_when_open() {
  screen -S dual-tape-watch-open -X quit 2>/dev/null || true
  screen -dmS dual-tape-watch-open zsh -lc "cd '$ROOT' && ./scripts/desk.sh watch-open >> '$RECON/dual_tape_watch_open.log' 2>&1"
}

find_node() {
  local dir bin newest cand
  if command -v node >/dev/null 2>&1; then
    bin="$(command -v node)"
    NODE_DIR="$(cd "$(dirname "$bin")" && pwd)"
    export PATH="$NODE_DIR:$PATH"
    echo "node: $NODE_DIR/node"
    return 0
  fi
  for dir in "$HOME/Documents/anaconda3/bin"; do
    if [[ -x "$dir/node" ]]; then
      NODE_DIR="$dir"
      export PATH="$NODE_DIR:$PATH"
      echo "node: $NODE_DIR/node"
      return 0
    fi
  done
  if [[ "${AAD_SKIP_SYSTEM_NODE_DIRS:-0}" != "1" ]]; then
    for dir in /opt/homebrew/bin /usr/local/bin; do
      if [[ -x "$dir/node" ]]; then
        NODE_DIR="$dir"
        export PATH="$NODE_DIR:$PATH"
        echo "node: $NODE_DIR/node"
        return 0
      fi
    done
  fi
  newest=""
  for cand in "$HOME"/.nvm/versions/node/*/bin; do
    if [[ -x "$cand/node" ]]; then
      newest="$cand"
    fi
  done
  if [[ -n "$newest" ]]; then
    newest="$(printf '%s\n' "$HOME"/.nvm/versions/node/*/bin | sort -V | tail -1)"
    if [[ -x "$newest/node" ]]; then
      NODE_DIR="$newest"
      export PATH="$NODE_DIR:$PATH"
      echo "node: $NODE_DIR/node"
      return 0
    fi
  fi
  echo "ERROR: node not found. Looked in PATH, $HOME/Documents/anaconda3/bin, /opt/homebrew/bin, /usr/local/bin, newest $HOME/.nvm/versions/node/*/bin" >&2
  return 1
}

start_web() {
  if lsof -tiTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
    return 0
  fi
  if [[ -z "$NODE_DIR" ]]; then
    find_node
  fi
  screen -S web-dev -X quit 2>/dev/null || true
  screen -dmS web-dev zsh -lc "export PATH='$NODE_DIR':\$PATH; cd '$ROOT/apps/web' && '$VITE' --host 127.0.0.1 --port 5173 >> '$RECON/web-dev.log' 2>&1"
}

start_api() {
  if lsof -tiTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
    return 0
  fi
  screen -S api-server -X quit 2>/dev/null || true
  screen -dmS api-server zsh -lc "cd '$ROOT' && PYTHONPATH=apps/api/src '$PY' -m uvicorn api.main:app --app-dir apps/api/src --host 127.0.0.1 --port 8000 >> '$RECON/api-server.log' 2>&1"
}

ensure_api_web() {
  start_api
  start_web
  sleep 4
}

ist_date() {
  if [[ -x "$PY" ]]; then
    "$PY" -c "from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo('Asia/Kolkata')).date())" 2>/dev/null && return 0
  fi
  TZ=Asia/Kolkata date +%F
}

recorder_pids() {
  pgrep -f '[Pp]ython.*-m marketdata --record-only' 2>/dev/null || true
}

recorder_screen_up() {
  screen -ls 2>/dev/null | grep -qE '[.]v2-recorder[[:space:]]'
}

recorder_is_running() {
  recorder_screen_up || [[ -n "$(recorder_pids)" ]]
}

recorder_start() {
  if recorder_is_running; then
    echo "ERROR: v2 recorder already running (screen $RECORDER_SCREEN). Refusing a second copy." >&2
    return 1
  fi
  if [[ ! -x "$V2_PY" ]]; then
    echo "ERROR: $V2_PY missing. Run ./scripts/mac_setup_v2.sh (does not touch .venv)." >&2
    return 1
  fi
  local wrap=""
  if [[ "$(uname -s)" == "Darwin" ]] && command -v caffeinate >/dev/null 2>&1; then
    wrap="caffeinate -dimsu "
  fi
  screen -dmS "$RECORDER_SCREEN" zsh -lc "cd '$ROOT' && ${wrap}'$V2_PY' -u -m marketdata --record-only"
  echo "v2 recorder STARTED (PAPER, record-only). screen=$RECORDER_SCREEN"
}

recorder_stop() {
  local pids
  pids="$(recorder_pids)"
  if [[ -n "$pids" ]]; then
    echo "Stopping v2 recorder: $pids"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    local i
    for i in 1 2 3 4 5 6 7 8 9 10; do
      pids="$(recorder_pids)"
      [[ -z "$pids" ]] && break
      sleep 1
    done
    pids="$(recorder_pids)"
    if [[ -n "$pids" ]]; then
      # shellcheck disable=SC2086
      kill -9 $pids 2>/dev/null || true
    fi
  fi
  screen -S "$RECORDER_SCREEN" -X quit 2>/dev/null || true
  echo "v2 recorder STOPPED (tapes left intact under data/tape/v2/)"
}

recorder_status() {
  local pids day log last
  pids="$(recorder_pids)"
  echo "v2 recorder process: ${pids:-STOPPED}"
  if recorder_screen_up; then
    echo "v2 recorder screen: $RECORDER_SCREEN UP"
  else
    echo "v2 recorder screen: $RECORDER_SCREEN DOWN"
  fi
  day="$(ist_date)"
  log="$TAPE_V2/$day/recorder.log"
  echo "v2 recorder log: $log"
  if [[ -f "$log" ]]; then
    last="$(tail -1 "$log" || true)"
    echo "v2 recorder last line: $last"
  else
    echo "v2 recorder last line: (no log yet for IST $day)"
  fi
}

# --- V2 paper stack (engine / health / gateway stub + recorder). No port 8000/5173. ---

v2_mode() {
  local m="${AAD_V2_MODE:-paper}"
  case "$m" in
    paper|replay) printf '%s' "$m" ;;
    *)
      echo "ERROR: V2 mode must be paper or replay (got $m). Live broker orders are refused." >&2
      return 1
      ;;
  esac
}

v2_state_dir() {
  printf '%s' "${AAD_STATE_DIR:-$ROOT/data/state}"
}

v2_caffeinate_prefix() {
  if [[ "$(uname -s)" == "Darwin" ]] && command -v caffeinate >/dev/null 2>&1; then
    printf '%s' "caffeinate -dimsu "
  fi
}

v2_screen_up() {
  local name="$1"
  screen -ls 2>/dev/null | grep -qE "[.]${name}[[:space:]]"
}

v2_engine_pids() {
  pgrep -f '[Pp]ython.*-m runtime engine' 2>/dev/null || true
}

v2_health_pids() {
  pgrep -f '[Pp]ython.*-m runtime health' 2>/dev/null || true
}

v2_gateway_pids() {
  pgrep -f '[Pp]ython.*-m runtime gateway' 2>/dev/null || true
}

v2_engine_running() {
  v2_screen_up "$ENGINE_SCREEN" || [[ -n "$(v2_engine_pids)" ]]
}

v2_health_running() {
  v2_screen_up "$HEALTH_SCREEN" || [[ -n "$(v2_health_pids)" ]]
}

v2_gateway_running() {
  v2_screen_up "$GATEWAY_SCREEN" || [[ -n "$(v2_gateway_pids)" ]]
}

v2_any_running() {
  recorder_is_running || v2_engine_running || v2_health_running || v2_gateway_running
}

v2_kill_pids() {
  local pids="$1" label="$2"
  if [[ -z "$pids" ]]; then
    return 0
  fi
  echo "Stopping $label: $pids"
  # shellcheck disable=SC2086
  kill $pids 2>/dev/null || true
  local i
  for i in 1 2 3 4 5 6 7 8 9 10; do
    # shellcheck disable=SC2086
    kill -0 $pids 2>/dev/null || break
    sleep 1
  done
  # shellcheck disable=SC2086
  kill -9 $pids 2>/dev/null || true
}

v2_start_engine() {
  if v2_engine_running; then
    echo "ERROR: v2 engine already running (screen $ENGINE_SCREEN). Refusing a second copy." >&2
    return 1
  fi
  local mode state wrap
  mode="$(v2_mode)" || return 1
  state="$(v2_state_dir)"
  mkdir -p "$state"
  wrap="$(v2_caffeinate_prefix)"
  screen -dmS "$ENGINE_SCREEN" zsh -lc "cd '$ROOT' && export AAD_STATE_DIR='$state' && ${wrap}'$V2_PY' -u -m runtime engine --mode '$mode' --state-dir '$state' >> '$RECON/v2-engine.log' 2>&1"
  echo "v2 engine STARTED (PAPER, mode=$mode, no live orders). screen=$ENGINE_SCREEN state=$state"
}

v2_start_health() {
  if v2_health_running; then
    echo "ERROR: v2 health already running (screen $HEALTH_SCREEN). Refusing a second copy." >&2
    return 1
  fi
  local state wrap
  state="$(v2_state_dir)"
  mkdir -p "$state"
  wrap="$(v2_caffeinate_prefix)"
  # No --once: loops writing health_status.json. Does not bind 8000/5173.
  screen -dmS "$HEALTH_SCREEN" zsh -lc "cd '$ROOT' && export AAD_STATE_DIR='$state' && ${wrap}'$V2_PY' -u -m runtime health --state-dir '$state' >> '$RECON/v2-health.log' 2>&1"
  echo "v2 health STARTED (PAPER). screen=$HEALTH_SCREEN state=$state"
}

v2_start_gateway() {
  if v2_gateway_running; then
    echo "ERROR: v2 gateway already running (screen $GATEWAY_SCREEN). Refusing a second copy." >&2
    return 1
  fi
  local mode state wrap
  mode="$(v2_mode)" || return 1
  state="$(v2_state_dir)"
  mkdir -p "$state"
  wrap="$(v2_caffeinate_prefix)"
  # On main, `python -m runtime gateway` is a stub: writes gateway.ready and exits.
  # Keep the screen so v2-status can see it. No HTTP listen — no clash with :8000/:5173.
  screen -dmS "$GATEWAY_SCREEN" zsh -lc "cd '$ROOT' && export AAD_STATE_DIR='$state' && ${wrap}'$V2_PY' -u -m runtime gateway --mode '$mode' --state-dir '$state' >> '$RECON/v2-gateway.log' 2>&1; echo 'gateway stub ready (no HTTP port)'; while true; do sleep 3600; done"
  echo "v2 gateway STARTED (PAPER stub, no HTTP port). screen=$GATEWAY_SCREEN state=$state"
}

v2_start() {
  local rc=0
  if [[ ! -x "$V2_PY" ]]; then
    echo "ERROR: $V2_PY missing. Run ./scripts/mac_setup_v2.sh (does not touch .venv)." >&2
    return 1
  fi
  v2_mode >/dev/null || return 1
  echo "=== v2-start (PAPER only; no live orders; no bind on 8000/5173) ==="
  echo "v2 python: $V2_PY ($("$V2_PY" -V 2>&1))"
  echo "v2 mode: $(v2_mode)  state: $(v2_state_dir)"
  if ! "$V2_PY" -c "import dhan_client, marketdata, contracts, events, runtime" >/dev/null 2>&1; then
    echo "ERROR: v2 imports failed in .venv-v2 (need dhan_client, marketdata, contracts, events, runtime). Re-run ./scripts/mac_setup_v2.sh" >&2
    return 1
  fi
  v2_start_engine || rc=1
  v2_start_health || rc=1
  v2_start_gateway || rc=1
  if token_keys_set; then
    recorder_start || rc=1
  else
    echo "WARNING: v2 recorder not started — DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN missing in .env (engine/health/gateway still run in paper/replay; recorder needs creds for the live feed). Values not printed."
  fi
  if [[ "$rc" -ne 0 ]]; then
    echo "v2-start completed with errors (duplicates or a service failed). PAPER. No live orders." >&2
    return "$rc"
  fi
  echo "v2 stack UP (PAPER). HTTP v2 routes stay on legacy :8000 only if events is importable in .venv; runtime gateway does not listen."
  return 0
}

v2_stop() {
  echo "=== v2-stop (leave tapes and state files intact) ==="
  recorder_stop
  v2_kill_pids "$(v2_engine_pids)" "v2 engine"
  v2_kill_pids "$(v2_health_pids)" "v2 health"
  v2_kill_pids "$(v2_gateway_pids)" "v2 gateway"
  screen -S "$ENGINE_SCREEN" -X quit 2>/dev/null || true
  screen -S "$HEALTH_SCREEN" -X quit 2>/dev/null || true
  screen -S "$GATEWAY_SCREEN" -X quit 2>/dev/null || true
  echo "v2 stack STOPPED (tapes under data/tape/v2/; state under $(v2_state_dir))"
}

v2_status_file_line() {
  local path="$1" label="$2"
  echo "$label: $path"
  if [[ -f "$path" ]]; then
    echo "$label last line: $(tail -1 "$path" || true)"
  else
    echo "$label last line: (missing)"
  fi
}

v2_status() {
  local state epids hpids gpids
  state="$(v2_state_dir)"
  epids="$(v2_engine_pids)"
  hpids="$(v2_health_pids)"
  gpids="$(v2_gateway_pids)"
  echo "=== v2 status (PAPER) ==="
  if [[ -x "$V2_PY" ]]; then
    echo "v2 python: $V2_PY ($("$V2_PY" -V 2>&1))"
  else
    echo "v2 python: $V2_PY MISSING"
  fi
  echo "v2 mode: ${AAD_V2_MODE:-paper}  state: $state"
  echo "v2 engine process: ${epids:-STOPPED}"
  if v2_screen_up "$ENGINE_SCREEN"; then
    echo "v2 engine screen: $ENGINE_SCREEN UP"
  else
    echo "v2 engine screen: $ENGINE_SCREEN DOWN"
  fi
  echo "v2 health process: ${hpids:-STOPPED}"
  if v2_screen_up "$HEALTH_SCREEN"; then
    echo "v2 health screen: $HEALTH_SCREEN UP"
  else
    echo "v2 health screen: $HEALTH_SCREEN DOWN"
  fi
  echo "v2 gateway process: ${gpids:-STOPPED}"
  if v2_screen_up "$GATEWAY_SCREEN"; then
    echo "v2 gateway screen: $GATEWAY_SCREEN UP"
  else
    echo "v2 gateway screen: $GATEWAY_SCREEN DOWN"
  fi
  echo "v2 gateway HTTP: none (runtime gateway is a stub; does not bind 8000/5173)"
  v2_status_file_line "$state/engine_status.json" "v2 engine status"
  v2_status_file_line "$state/health_status.json" "v2 health status"
  v2_status_file_line "$state/gateway.ready" "v2 gateway ready"
  recorder_status
}

token_file_present() {
  # Presence only. Never print values.
  local envf="$ROOT/.env"
  [[ -f "$envf" ]]
}

token_keys_set() {
  local envf="$ROOT/.env"
  [[ -f "$envf" ]] || return 1
  grep -qE '^[[:space:]]*DHAN_CLIENT_ID=.' "$envf" && grep -qE '^[[:space:]]*DHAN_ACCESS_TOKEN=.' "$envf"
}

preflight() {
  local rc=0
  echo "=== desk.sh preflight ==="
  if [[ -x "$PY" ]]; then
    echo "legacy python: $PY ($("$PY" -V 2>&1))"
  else
    echo "ERROR: legacy .venv python missing at $PY (legacy desk cannot start)" >&2
    rc=1
  fi
  if [[ -x "$V2_PY" ]]; then
    echo "v2 python: $V2_PY ($("$V2_PY" -V 2>&1))"
  else
    echo "WARNING: v2 python missing at $V2_PY — run ./scripts/mac_setup_v2.sh (does not stop the legacy desk)"
  fi

  if [[ -x "$PY" ]]; then
    if ! "$PY" -c "import fastapi, desk_ml, trading_agents_india" >/dev/null 2>&1; then
      echo "ERROR: legacy imports failed (fastapi / desk_ml / trading_agents_india)" >&2
      rc=1
    else
      echo "legacy imports: ok (fastapi, desk_ml, trading_agents_india)"
    fi
    if ! PYTHONPATH="$ROOT/apps/api/src${PYTHONPATH:+:$PYTHONPATH}" \
      "$PY" -c "from api.main import create_app; create_app()" >/dev/null 2>&1; then
      echo "ERROR: api.main create_app() failed in legacy venv" >&2
      rc=1
    else
      echo "legacy api.main: ok"
    fi
  fi

  if [[ -x "$V2_PY" ]]; then
    if ! "$V2_PY" -c "import dhan_client, marketdata, contracts, events, runtime" >/dev/null 2>&1; then
      echo "WARNING: v2 imports failed in .venv-v2 (dhan_client / marketdata / contracts / events / runtime) — v2-start will not start"
    else
      echo "v2 imports: ok (dhan_client, marketdata, contracts, events, runtime)"
    fi
    echo "v2 mode: ${AAD_V2_MODE:-paper} (paper|replay only; live refused)"
    echo "v2 gateway: python -m runtime gateway (stub, no HTTP; does not bind 8000/5173)"
  fi

  if find_node; then
    echo "node path: $NODE_DIR"
  else
    echo "ERROR: node is required for the website (port 5173)" >&2
    rc=1
  fi

  if token_file_present; then
    if token_keys_set; then
      echo "Dhan token file: .env present (DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN keys set; values not printed)"
    else
      echo "WARNING: Dhan token file .env present but DHAN_CLIENT_ID / DHAN_ACCESS_TOKEN empty or missing (fixtures only)"
    fi
  else
    echo "WARNING: Dhan token file .env missing (fixtures only; does not stop the legacy desk)"
  fi

  if [[ "$rc" -ne 0 ]]; then
    echo "preflight FAILED (legacy desk would not start)" >&2
    return "$rc"
  fi
  echo "preflight OK (legacy desk can start)"
  return 0
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

if [[ "${DESK_SH_SOURCED:-0}" == "1" ]]; then
  return 0
fi

case "$CMD" in
  preflight)
    preflight
    ;;
  morning|start)
    preflight
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
    start_api
    start_web
    arm_dual_tape_when_open
    sleep 2
    write_status
    echo "MORNING UP. Desk http://127.0.0.1:5173/desk  Founder http://127.0.0.1:5173/pm"
    echo "On /pm: pick index then START TRADE. PAPER. No live orders."
    screen -ls || true
    ;;
  close|night|nightly|stop-all)
    echo "CLOSE: stop data capture + ALL V2, keep website, honesty exam + nightly."
    stop_dual_tape
    v2_stop
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
    preflight
    stop_dual_tape
    ensure_api_web
    write_status " website-only"
    echo "Website ON. Capture OFF. http://127.0.0.1:5173/desk"
    ;;
  recorder-start)
    recorder_start
    ;;
  recorder-stop)
    recorder_stop
    ;;
  recorder-status)
    recorder_status
    ;;
  v2-start)
    v2_start
    ;;
  v2-stop)
    v2_stop
    ;;
  v2-status)
    v2_status
    ;;
  start-all)
    preflight
    stop_dual_tape
    ensure_api_web
    write_status " start-all"
    echo "Website ON (legacy :8000 / :5173). Capture armed via watch-open. PAPER."
    arm_dual_tape_when_open
    v2_start
    ;;
  status)
    write_status
    echo "=== desk status ==="
    echo "API  : $(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null | head -1 || echo DOWN)  http://127.0.0.1:8000/health"
    echo "WEB  : $(lsof -tiTCP:5173 -sTCP:LISTEN 2>/dev/null | head -1 || echo DOWN)  http://127.0.0.1:5173/desk"
    echo "TAPE : $(pgrep -f 'trading_agents_india dual-tape' | head -1 || echo STOPPED)"
    v2_status
    echo "Honesty: http://127.0.0.1:5173/pm  and  data/recon/sod_exam_report.json"
    echo "Nightly: data/recon/\$(IST-date).json  and  teams/02_phd_math/docs/handoffs/NIGHTLY_*.md"
    if [[ -f "$RECON/close_status.txt" ]]; then
      echo "--- last close ---"
      cat "$RECON/close_status.txt"
    fi
    ;;
  watch-open)
    echo "dual-tape watch-open: Mon–Fri 09:30–15:29 IST capture window."
    rm -f "$RECON/paper_dual_tape_STOPPED.flag"
    if ! "$PY" -u - <<'PY'
from datetime import datetime
from zoneinfo import ZoneInfo
import sys
import time

ist = ZoneInfo("Asia/Kolkata")
now = datetime.now(ist)
if now.weekday() >= 5:
    print(f"WEEKEND ({now.date()}): no dual-tape", flush=True)
    sys.exit(2)
target = now.replace(hour=9, minute=30, second=0, microsecond=0)
end = now.replace(hour=15, minute=29, second=0, microsecond=0)
if now >= end:
    print(f"past 15:29 IST ({now.isoformat()}); capture closed for today", flush=True)
    sys.exit(3)
if now < target:
    secs = int((target - now).total_seconds())
    print(
        f"waiting until 09:30 IST ({target.isoformat()}) — ~{secs}s — "
        "cash opened 09:15; first NEW paper + dual-tape ticks at 09:30",
        flush=True,
    )
    while datetime.now(ist) < target:
        time.sleep(20)
else:
    print(f"past 09:30 IST ({now.isoformat()}); starting dual-tape now", flush=True)
PY
    then
      rc=$?
      echo "watch-open aborted (rc=$rc). See data/recon/dual_tape_watch_open.log"
      exit "$rc"
    fi
    if pgrep -f 'trading_agents_india dual-tape' >/dev/null 2>&1; then
      echo "dual-tape already running — skip second start"
    else
      start_dual_tape
      echo "dual-tape STARTED (PAPER). execution=refused"
    fi
    sleep 4
    write_status " watch-open"
    screen -ls || true
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
    echo "usage: $0 morning|close|website|status|watch-open|watch-close|preflight|recorder-start|recorder-stop|recorder-status|v2-start|v2-stop|v2-status|start-all|stop-all" >&2
    exit 2
    ;;
esac
