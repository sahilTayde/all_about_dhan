#!/usr/bin/env bash
# Founder one-command day. PAPER only. No live orders. NO_PROMOTE.
#
#   ./scripts/desk.sh preflight        # versions, imports (incl. desk.paper / risk_engine), node, token file
# PYTHONPATH: allowlisted legacy packages/*/src only (desk, risk-engine, brokers, health).
# Mac: just ./scripts/desk.sh morning  or  ./scripts/desk.sh watch-open  — no manual export.
#   ./scripts/desk.sh mint-token       # C5-06 optional TOTP mint → .env DHAN_ACCESS_TOKEN
# C5-06 hook (OFF tonight): before a pre-10:22 CT desk start, Sahil may run
#   ./scripts/mint_dhan_token.sh --check   then   ./scripts/desk.sh mint-token
# morning does NOT mint. Paper only. Never prints PIN / TOTP / accessToken.
#   ./scripts/desk.sh morning          # preflight + API + website + dual-tape (09:00 IST)
#   ./scripts/desk.sh website          # preflight + API + website only (no data capture)
#   ./scripts/desk.sh watch-open       # wait until 09:30 IST Mon–Fri, then dual-tape
#   ./scripts/desk.sh recorder-start   # v2 marketdata --record-only in .venv-v2 (screen v2-recorder)
#   ./scripts/desk.sh recorder-stop    # stop v2 recorder; leave tapes intact
#   ./scripts/desk.sh recorder-status  # process + last line of today's IST recorder.log
#   ./scripts/desk.sh shadow-start     # optional V2 paper shadow (log-only; never blocks legacy)
#   ./scripts/desk.sh shadow-stop      # stop V2 shadow; leave data/shadow/v2 journals
#   ./scripts/desk.sh shadow-status    # process + last status.json
#   ./scripts/desk.sh c5-start         # shared runtime signal once + <=5 customer execs (paper only)
#   ./scripts/desk.sh c5-status        # last C5 launch + ready files (no re-plan)
#   ./scripts/desk.sh c5-stop          # mark C5 stopped; leave paper ledgers
#   ./scripts/desk.sh c5-backup        # tarball of data/c5 paper state
#   ./scripts/desk.sh c5-restore       # restore dry-run (needs --snapshot)
#   ./scripts/desk.sh close            # after 15:30: stop capture + v2 recorder + shadow, keep website, honesty + nightly
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
SHADOW_DIR="${AAD_SHADOW:-$ROOT/data/shadow/v2}"
SHADOW_BASKET="${AAD_SHADOW_BASKET:-$ROOT/config/v2/baskets/approved_paper_shadow.yaml}"
RECORDER_SCREEN="v2-recorder"
SHADOW_SCREEN="v2-shadow"
NODE_DIR="${NODE_DIR:-}"
mkdir -p "$RECON"
CMD="${1:-status}"

# Legacy .venv is CPython 3.9.6 and does not pip-install desk / risk-engine / brokers / health.
# Dual-tape paper book needs those four on PYTHONPATH (health.supervise wraps the loop).
# Do NOT dump every packages/*/src: v2-only trees (contracts, events, runtime, oms,
# control, boss, marketdata, data-recorder, …) use PEP 604 unions (str | T) and raise
# TypeError on 3.9 when imported. That aborted preflight create_app() after PR #70.
# A named loop (not ls|tr) stays correct on bash 3.2 / BSD when a package dir is missing.
legacy_src_path() {
  local name d acc=""
  for name in desk risk-engine brokers health; do
    d="$ROOT/packages/$name/src"
    [[ -d "$d" ]] || continue
    acc="${acc:+$acc:}$d"
  done
  printf '%s' "$acc"
}

ensure_legacy_pythonpath() {
  local extra
  extra="$(legacy_src_path)"
  if [[ -n "$extra" ]]; then
    case ":${PYTHONPATH:-}:" in
      *":$ROOT/packages/desk/src:"*) ;;
      *) export PYTHONPATH="${extra}${PYTHONPATH:+:$PYTHONPATH}" ;;
    esac
  fi
}

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
  # Bake PYTHONPATH into the login zsh so a Mac .zprofile cannot drop packages/*/src.
  screen -dmS dual-tape-live-2s zsh -lc "cd '$ROOT' && export PYTHONPATH='$PYTHONPATH' && $inner"
}

arm_dual_tape_when_open() {
  screen -S dual-tape-watch-open -X quit 2>/dev/null || true
  screen -dmS dual-tape-watch-open zsh -lc "cd '$ROOT' && ./scripts/desk.sh watch-open >> '$RECON/dual_tape_watch_open.log' 2>&1"
}

find_node() {
  local dir bin newest cand ver newest_ver
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
  newest_ver=""
  for cand in "$HOME"/.nvm/versions/node/*/bin; do
    if [[ -x "$cand/node" ]]; then
      ver="${cand%/bin}"
      ver="${ver##*/}"
      ver="${ver#v}"
      newest_ver="${newest_ver}${ver}"$'\n'
    fi
  done
  # bash 3.2 + BSD sort: no GNU -V. Numeric dotted compare on stripped vX.Y.Z.
  if [[ -n "$newest_ver" ]]; then
    newest_ver="$(printf '%s' "$newest_ver" | sort -t. -k1,1n -k2,2n -k3,3n | tail -1)"
    newest="$HOME/.nvm/versions/node/v${newest_ver}/bin"
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
  # Keep allowlisted packages (desk / risk_engine / brokers / health) and prepend the API app dir.
  screen -dmS api-server zsh -lc "cd '$ROOT' && PYTHONPATH='apps/api/src${PYTHONPATH:+:$PYTHONPATH}' '$PY' -m uvicorn api.main:app --app-dir apps/api/src --host 127.0.0.1 --port 8000 >> '$RECON/api-server.log' 2>&1"
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
  screen -S "$RECORDER_SCREEN" -X quit >/dev/null 2>&1 || true
  echo "v2 recorder STOPPED (tapes left intact under $TAPE_V2)"
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

shadow_pids() {
  pgrep -f '[Pp]ython.*-m shadow (run|follow)' 2>/dev/null || true
}

shadow_screen_up() {
  screen -ls 2>/dev/null | grep -qE '[.]v2-shadow[[:space:]]'
}

shadow_is_running() {
  shadow_screen_up || [[ -n "$(shadow_pids)" ]]
}

shadow_prove_follower() {
  # import shadow is not enough: runtime/__init__ used to pull brokers via recovery.
  local err
  if ! err="$("$V2_PY" -c "import shadow.runner" 2>&1)"; then
    echo "ERROR: import shadow.runner failed in .venv-v2 — shadow will not start (legacy desk still runs)" >&2
    printf '%s\n' "$err" | tail -8 >&2
    return 1
  fi
  if ! err="$("$V2_PY" -m shadow -h 2>&1)"; then
    echo "ERROR: python -m shadow failed in .venv-v2 — shadow will not start (legacy desk still runs)" >&2
    printf '%s\n' "$err" | tail -8 >&2
    return 1
  fi
}

shadow_start() {
  if shadow_is_running; then
    echo "ERROR: v2 shadow already running (screen $SHADOW_SCREEN). Refusing a second copy." >&2
    return 1
  fi
  if [[ ! -x "$V2_PY" ]]; then
    echo "ERROR: $V2_PY missing. Run ./scripts/mac_setup_v2.sh (does not touch .venv)." >&2
    return 1
  fi
  shadow_prove_follower || return 1
  if [[ ! -f "$SHADOW_BASKET" ]]; then
    echo "WARNING: founder-approved paper/shadow basket missing ($SHADOW_BASKET). V2 shadow will fail closed (NO_BASKET). Dual-tape is unchanged." >&2
  else
    echo "v2 shadow basket: $SHADOW_BASKET (paper/shadow only; does not replace dual-tape)"
  fi
  mkdir -p "$SHADOW_DIR"
  rm -f "$SHADOW_DIR/STOPPED.flag"
  local wrap="" day i
  day="$(ist_date)"
  if [[ "$(uname -s)" == "Darwin" ]] && command -v caffeinate >/dev/null 2>&1; then
    wrap="caffeinate -dimsu "
  fi
  # Follow today's recorder tape read-only. Missing tape fails closed (no invented ticks).
  screen -dmS "$SHADOW_SCREEN" zsh -lc "cd '$ROOT' && ${wrap}'$V2_PY' -u -m shadow follow --state-dir '$SHADOW_DIR' --tape '$TAPE_V2/$day' --day '$day' --stop-flag '$SHADOW_DIR/STOPPED.flag' >> '$SHADOW_DIR/shadow.log' 2>&1"
  for i in 1 2 3 4 5 6; do
    if shadow_is_running; then
      echo "v2 shadow STARTED (PAPER, log-only, account=v2-shadow). screen=$SHADOW_SCREEN"
      echo "v2 shadow does not own the live paper book. Legacy dual-tape still does."
      return 0
    fi
    sleep 0.5
  done
  echo "ERROR: v2 shadow follower died after start (fail closed). Last log:" >&2
  if [[ -f "$SHADOW_DIR/shadow.log" ]]; then
    tail -20 "$SHADOW_DIR/shadow.log" >&2 || true
  else
    echo "(no $SHADOW_DIR/shadow.log)" >&2
  fi
  screen -S "$SHADOW_SCREEN" -X quit >/dev/null 2>&1 || true
  return 1
}

shadow_stop() {
  local pids
  mkdir -p "$SHADOW_DIR"
  touch "$SHADOW_DIR/STOPPED.flag"
  pids="$(shadow_pids)"
  if [[ -n "$pids" ]]; then
    echo "Stopping v2 shadow: $pids"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    local i
    for i in 1 2 3 4 5 6 7 8 9 10; do
      pids="$(shadow_pids)"
      [[ -z "$pids" ]] && break
      sleep 1
    done
    pids="$(shadow_pids)"
    if [[ -n "$pids" ]]; then
      # shellcheck disable=SC2086
      kill -9 $pids 2>/dev/null || true
    fi
  fi
  screen -S "$SHADOW_SCREEN" -X quit >/dev/null 2>&1 || true
  echo "v2 shadow STOPPED (journals left intact under $SHADOW_DIR)"
}

shadow_status() {
  local pids day status last
  pids="$(shadow_pids)"
  echo "v2 shadow process: ${pids:-STOPPED}"
  if shadow_screen_up; then
    echo "v2 shadow screen: $SHADOW_SCREEN UP"
  else
    echo "v2 shadow screen: $SHADOW_SCREEN DOWN"
  fi
  day="$(ist_date)"
  status="$SHADOW_DIR/$day/status.json"
  echo "v2 shadow status: $status"
  if [[ -f "$status" ]]; then
    last="$(tail -1 "$status" || true)"
    echo "v2 shadow last status: $last"
  else
    echo "v2 shadow last status: (no status yet for IST $day)"
  fi
  echo "v2 shadow log: $SHADOW_DIR/shadow.log"
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
    # Same env dual-tape uses. Fail before open if desk.paper / risk_engine cannot import.
    local _imp _mod _err
    for _mod in desk.paper risk_engine; do
      _err="$("$PY" -c "import ${_mod}" 2>&1)" && _imp=0 || _imp=$?
      if [[ "$_imp" -ne 0 ]]; then
        echo "ERROR: cannot import ${_mod} with $PY (PYTHONPATH=${PYTHONPATH:-empty})" >&2
        echo "$_err" | head -5 >&2
        rc=1
      else
        echo "legacy import ${_mod}: ok"
      fi
    done
    if ! PYTHONPATH="$ROOT/apps/api/src${PYTHONPATH:+:$PYTHONPATH}" \
      "$PY" -c "from api.main import create_app; create_app()" >/dev/null 2>&1; then
      echo "ERROR: api.main create_app() failed in legacy venv" >&2
      rc=1
    else
      echo "legacy api.main: ok"
    fi
  fi

  if [[ -x "$V2_PY" ]]; then
    if ! "$V2_PY" -c "import dhan_client, marketdata" >/dev/null 2>&1; then
      echo "WARNING: v2 imports failed in .venv-v2 (dhan_client / marketdata) — recorder will not start (legacy desk still starts)"
    else
      echo "v2 imports: ok (dhan_client, marketdata)"
    fi
    if ! "$V2_PY" -c "import shadow.runner" >/dev/null 2>&1; then
      echo "WARNING: shadow.runner import failed in .venv-v2 — shadow-start will not run (legacy desk still starts)"
    else
      echo "v2 imports: ok (shadow.runner)"
    fi
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

ensure_legacy_pythonpath

if [[ "${DESK_SH_SOURCED:-0}" == "1" ]]; then
  return 0
fi

case "$CMD" in
  preflight)
    preflight
    ;;
  mint-token)
    shift
    exec "$ROOT/scripts/mint_dhan_token.sh" "$@"
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
  close|night|nightly)
    echo "CLOSE: stop data capture, keep website, honesty exam + nightly."
    stop_dual_tape
    recorder_stop || echo "WARNING: v2 recorder stop failed (legacy close continues)" >&2
    shadow_stop || echo "WARNING: v2 shadow stop failed (legacy close continues)" >&2
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
  shadow-start)
    shadow_start || echo "WARNING: v2 shadow-start failed (legacy desk is unchanged)" >&2
    ;;
  shadow-stop)
    shadow_stop || echo "WARNING: v2 shadow-stop failed (legacy desk is unchanged)" >&2
    ;;
  shadow-status)
    shadow_status
    ;;
  c5-start|c5-status|c5-stop|c5-backup|c5-restore|c5-plan)
    shift
    "$ROOT/scripts/c5_ops.sh" "${CMD#c5-}" "$@"
    ;;
  status)
    write_status
    echo "=== desk status ==="
    echo "API  : $(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null | head -1 || echo DOWN)  http://127.0.0.1:8000/health"
    echo "WEB  : $(lsof -tiTCP:5173 -sTCP:LISTEN 2>/dev/null | head -1 || echo DOWN)  http://127.0.0.1:5173/desk"
    echo "TAPE : $(pgrep -f 'trading_agents_india dual-tape' | head -1 || echo STOPPED)"
    recorder_status
    shadow_status
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
    echo "usage: $0 morning|close|website|status|watch-open|watch-close|preflight|recorder-start|recorder-stop|recorder-status|shadow-start|shadow-stop|shadow-status|c5-start|c5-status|c5-stop|c5-backup|c5-restore|mint-token" >&2
    exit 2
    ;;
esac
