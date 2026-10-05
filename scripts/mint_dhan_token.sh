#!/usr/bin/env bash
# C5-06 Mac paper desk: mint a 24h Dhan accessToken via official TOTP.
#
#   ./scripts/mint_dhan_token.sh --check   # names present? no HTTP
#   ./scripts/mint_dhan_token.sh           # POST generateAccessToken → repo-root .env
#
# Reads DHAN_CLIENT_ID / DHAN_PIN / DHAN_TOTP_SECRET from env or macOS Keychain
# (account all_about_dhan). Writes DHAN_ACCESS_TOKEN to repo-root .env — the
# same file scripts/desk.sh already reads. Never prints secrets. Never live orders.
# desk.sh morning does NOT call this (opt-in before a pre-10:22 CT start).
set -euo pipefail
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${AAD_ROOT:-$(cd "$_SCRIPT_DIR/.." && pwd)}"
cd "$ROOT"

if [[ -x "${AAD_V2_PY:-}" ]]; then
  PY="$AAD_V2_PY"
elif [[ -x "$ROOT/.venv-v2/bin/python" ]]; then
  PY="$ROOT/.venv-v2/bin/python"
elif [[ -x "${AAD_PY:-}" ]]; then
  PY="$AAD_PY"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="${PYTHON:-python3}"
fi

if [[ ! -x "$PY" ]] && ! command -v "$PY" >/dev/null 2>&1; then
  echo "ERROR: python missing for mint-token (set AAD_V2_PY or run ./scripts/mac_setup_v2.sh)" >&2
  exit 2
fi

exec "$PY" -m dhan_client mint-token "$@"
