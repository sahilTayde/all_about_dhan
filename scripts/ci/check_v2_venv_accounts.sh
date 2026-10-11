#!/usr/bin/env bash
# Prove the Mac .venv-v2 third-party spec can load config/v2/accounts.yaml.
# Uses a throwaway venv so CI's hash-pinned env cannot hide a missing V2 dep.
# PAPER only. No live broker. No secrets.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORKDIR="${AAD_V2_VENV_CHECK:-$(mktemp -d "${TMPDIR:-/tmp}/aad-v2-venv.XXXXXX")}"
mkdir -p "$WORKDIR"
VENV="$WORKDIR/venv-v2"
echo "check_v2_venv_accounts: root=$ROOT venv=$VENV"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install -U pip
"$VENV/bin/python" -m pip install --require-hashes -r "$ROOT/requirements/v2.txt"
"$VENV/bin/python" -m pip install --no-deps \
  -e "$ROOT/packages/contracts" \
  -e "$ROOT/packages/accounts"
"$VENV/bin/python" -c "import yaml, accounts; print('v2-venv imports ok', yaml.__name__, accounts.__name__)"
out="$("$VENV/bin/python" -m accounts list)"
printf '%s\n' "$out"
AAD_ACCOUNTS_LIST_JSON="$out" "$VENV/bin/python" - <<'PY'
import json
import os
import sys

raw = os.environ["AAD_ACCOUNTS_LIST_JSON"]
body = json.loads(raw)
if body.get("ok") is not True:
    sys.exit(f"accounts list not ok: {body!r}")
if body.get("default_account") != "founder":
    sys.exit(f"unexpected default_account: {body!r}")
if "YAML_UNAVAILABLE" in raw:
    sys.exit("YAML_UNAVAILABLE in accounts list output")
print("v2-venv accounts.yaml load ok", len(body.get("accounts") or []))
PY
