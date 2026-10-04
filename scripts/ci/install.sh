#!/usr/bin/env bash
# CI / fresh-machine install. Third-party packages only from the hash-pinned lock; every in-repo
# package from this checkout with --no-deps, so no local name (desk, ledger, events, ...) can
# resolve from a package index. Same recipe works on the Mac and the VPS.
set -euo pipefail
cd "$(dirname "$0")/../.."
python -m pip install --require-hashes -r requirements/ci.txt
args=()
for p in dhan-client marketdata indicators backtest ledger risk-engine brokers health data-recorder desk-intel docs-auditor \
         agent_rag warehouse premarket trading_agents_india events contracts strategies desk-ml analysts boss desk runtime oms control shadow secretstore; do
  args+=(-e "packages/$p")
done
args+=(-e apps/api)
python -m pip install --no-deps --no-build-isolation "${args[@]}"
python scripts/ci/check_local_names.py
