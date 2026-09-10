#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for all_about_dhan.
# Sets up a Python venv with the editable monorepo packages plus the Vite web app.
# Safe to run repeatedly. No secrets, no live Dhan, no npm restarts of running servers.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# python3-venv is required to create virtualenvs on Debian/Ubuntu base images.
if ! python3 -c 'import ensurepip' >/dev/null 2>&1; then
  echo "[install] installing python3-venv"
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends python3-venv
fi

# Python virtualenv + editable monorepo packages (dependency order matters:
# dhan-client and backtest-engine are local deps of other packages / apps/api).
if [ ! -x ".venv/bin/python" ]; then
  echo "[install] creating .venv"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip

python -m pip install \
  -e packages/dhan-client \
  -e packages/backtest \
  -e packages/desk-intel \
  -e packages/docs-auditor \
  -e packages/agent_rag \
  -e packages/warehouse \
  -e packages/trading_agents_india \
  -e apps/api \
  pytest

# Web app dependencies (mock-data customer desk; no Dhan in the browser).
if [ -d apps/web ]; then
  echo "[install] installing apps/web node deps"
  ( cd apps/web && npm ci )
fi

# Cursor Cloud secrets are injected as process env vars — never via git.
# Materialize a gitignored .env so load_dotenv() paths work on the VM.
# Values are not printed.
python3 - <<'PY'
from pathlib import Path
import os

root = Path.cwd()
keys = [
    "YOUTUBE_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "GEMINI_KEY",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "COUNSEL_PROVIDER",
    "DHAN_CLIENT_ID",
    "DHAN_ACCESS_TOKEN",
    "DHAN_REFRESH_TOKEN",
    "DHAN_CLIENT_SECRET",
]
lines = []
present = 0
for key in keys:
    val = os.environ.get(key)
    if val is None or not str(val).strip():
        continue
    present += 1
    # Preserve value as-is; do not log it.
    lines.append(f"{key}={val}\n")
# Paper default: news veto stays off unless the environment overrides it.
if "NEWS_VETO_ENABLED" not in os.environ:
    lines.append("NEWS_VETO_ENABLED=false\n")
elif str(os.environ.get("NEWS_VETO_ENABLED") or "").strip():
    lines.append(f"NEWS_VETO_ENABLED={os.environ['NEWS_VETO_ENABLED']}\n")

path = root / ".env"
if lines:
    path.write_text("".join(lines), encoding="utf-8")
    path.chmod(0o600)
    print(f"[install] wrote gitignored .env with {present} secret keys from environ (values not logged)")
else:
    print("[install] no cloud secrets in environ — dry-run / fixtures only")
PY

echo "[install] done"
