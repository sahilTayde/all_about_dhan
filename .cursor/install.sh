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
  -e packages/trading_agents_india \
  -e apps/api \
  pytest

# Web app dependencies (mock-data customer desk; no Dhan in the browser).
if [ -d apps/web ]; then
  echo "[install] installing apps/web node deps"
  ( cd apps/web && npm ci )
fi

echo "[install] done"
