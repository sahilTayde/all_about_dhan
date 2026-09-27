#!/usr/bin/env bash
# One pytest run per package, sockets disabled (a test that reaches the network fails), no live env.
set -uo pipefail
cd "$(dirname "$0")/../.."
python - <<'PY'
import os, sys
bad = [k for k in os.environ if k.startswith("DHAN_") or k == "ALL_ABOUT_DHAN_LIVE_CONFIRM"]
sys.exit(f"broker credentials / live confirm must not be set in CI: {bad}" if bad else 0)
PY
rc=0
for t in packages/*/tests apps/api/tests tests/regression; do
  [ -d "$t" ] || continue
  echo "::group::$t"
  python -m pytest -q -p no:cacheprovider --allow-hosts=127.0.0.1,localhost --allow-unix-socket \
    -m "not network and not sim and not slow" "$t" || rc=1
  echo "::endgroup::"
done
exit $rc
