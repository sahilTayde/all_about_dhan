#!/usr/bin/env bash
# Build an isolated .venv-v2 for the V2 paper stack (recorder + runtime).
# Idempotent. Never touches the legacy Mac .venv (Python 3.9).
# PAPER only. No live orders. DhanBroker is never constructed here.
#
#   ./scripts/mac_setup_v2.sh
#
set -euo pipefail
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${AAD_ROOT:-$(cd "$_SCRIPT_DIR/.." && pwd)}"
VENV="${AAD_V2_VENV:-$ROOT/.venv-v2}"
LEGACY="$ROOT/.venv"

echo "mac_setup_v2: repo=$ROOT"
echo "mac_setup_v2: v2 venv=$VENV (legacy .venv is not used)"

_abs() {
  local p="$1" parent
  parent="$(cd "$(dirname "$p")" 2>/dev/null && pwd)" || return 1
  printf "%s/%s" "$parent" "$(basename "$p")"
}
VENV_ABS="$(_abs "$VENV" || echo "$VENV")"
LEGACY_ABS="$(_abs "$LEGACY" || echo "$LEGACY")"
if [[ "$VENV" == "$LEGACY" || "$VENV_ABS" == "$LEGACY_ABS" ]]; then
  echo "ERROR: refusing to install v2 packages into the legacy .venv" >&2
  exit 1
fi
if [[ -d "$LEGACY" ]] && command -v realpath >/dev/null 2>&1; then
  if [[ "$(realpath "$VENV" 2>/dev/null || true)" == "$(realpath "$LEGACY")" ]]; then
    echo "ERROR: refusing to install v2 packages into the legacy .venv" >&2
    exit 1
  fi
fi

UV=""
if command -v uv >/dev/null 2>&1; then
  UV="$(command -v uv)"
elif [[ -x "$HOME/.local/bin/uv" ]]; then
  UV="$HOME/.local/bin/uv"
fi

create_venv() {
  if [[ -n "$UV" ]]; then
    echo "mac_setup_v2: creating venv with uv ($UV)"
    "$UV" venv "$VENV" --python 3.11 || "$UV" venv "$VENV" --python 3.12
    return 0
  fi
  local py=""
  if command -v python3.11 >/dev/null 2>&1; then
    py="python3.11"
  elif command -v python3.12 >/dev/null 2>&1; then
    py="python3.12"
  fi
  if [[ -z "$py" ]]; then
    echo "ERROR: need uv or python3.11/python3.12 to build .venv-v2 (legacy .venv left untouched)" >&2
    exit 1
  fi
  echo "mac_setup_v2: creating venv with $py -m venv (uv not found)"
  "$py" -m venv "$VENV"
}

if [[ ! -x "$VENV/bin/python" ]]; then
  create_venv
else
  echo "mac_setup_v2: $VENV already exists — reusing (idempotent)"
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "ERROR: $VENV/bin/python missing after create" >&2
  exit 1
fi

echo "mac_setup_v2: v2 python is $($VENV/bin/python -V 2>&1)"

# Third-party deps the V2 packages import. Local packages are then installed
# --no-deps so names like events/desk never resolve from PyPI (same as CI).
# Skip the legacy stack (boss / analysts / paper_scalp). Those stay in .venv.
V2_THIRD=(jsonschema referencing rfc3339-validator PyYAML prometheus-client)
# Recorder + runtime engine/health/gateway (+ packages those import).
V2_PKGS=(
  dhan-client
  contracts
  events
  marketdata
  risk-engine
  ledger
  health
  indicators
  brokers
  strategies
  runtime
  oms
)

install_third() {
  echo "mac_setup_v2: third-party ${V2_THIRD[*]}"
  if [[ -n "$UV" ]]; then
    "$UV" pip install --python "$VENV/bin/python" "${V2_THIRD[@]}"
  else
    "$VENV/bin/python" -m pip install -U pip
    "$VENV/bin/python" -m pip install "${V2_THIRD[@]}"
  fi
}

install_local() {
  local args=() p
  for p in "${V2_PKGS[@]}"; do
    args+=(-e "$ROOT/packages/$p")
  done
  echo "mac_setup_v2: editable ${V2_PKGS[*]} (--no-deps)"
  if [[ -n "$UV" ]]; then
    "$UV" pip install --python "$VENV/bin/python" --no-deps "${args[@]}"
  else
    "$VENV/bin/python" -m pip install --no-deps "${args[@]}"
  fi
}

install_third
install_local

"$VENV/bin/python" -c "import dhan_client, marketdata, contracts, events, runtime; print('mac_setup_v2: imports ok', dhan_client.__name__, marketdata.__name__, runtime.__name__)"
echo "mac_setup_v2: done. Legacy .venv was not modified."
echo "Next: ./scripts/desk.sh v2-start   # or recorder-start for the tape only"
