#!/usr/bin/env bash
# Build an isolated .venv-v2 for the V2 marketdata recorder.
# Idempotent. Never touches the legacy Mac .venv (Python 3.9).
# PAPER only. No live orders.
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

if [[ -n "$UV" ]]; then
  "$UV" pip install --python "$VENV/bin/python" -e "$ROOT/packages/dhan-client" -e "$ROOT/packages/marketdata"
else
  "$VENV/bin/python" -m pip install -U pip
  "$VENV/bin/python" -m pip install -e "$ROOT/packages/dhan-client" -e "$ROOT/packages/marketdata"
fi

"$VENV/bin/python" -c "import dhan_client, marketdata; print('mac_setup_v2: imports ok', dhan_client.__name__, marketdata.__name__)"
echo "mac_setup_v2: done. Legacy .venv was not modified."
echo "Next: ./scripts/desk.sh recorder-start"
