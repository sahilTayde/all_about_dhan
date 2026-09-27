"""PR check: strategy / risk / cost changes need the honest-backtest section filled in.

    python tools/backtest_gate/pr_check.py --base <sha> --head <sha>     # CI (body from $GITHUB_EVENT_PATH)
    python tools/backtest_gate/pr_check.py --body-file body.md --changed a.py b.yaml

Rules:
- No gated path changed: pass.
- Gated code/config changed, expected results unchanged: every field present; `N/A: <reason>` allowed
  (the gate already proved the synthetic results did not move).
- `expected_results.json` changed (results moved): OOS results, costs, DSR and trial count must be
  real values; N/A is refused. DSR and trial count need a number.

The PR body is untrusted input: it is read from the event file, never interpolated into a shell.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

EXPECTED_REL = "tools/backtest_gate/expected_results.json"
GATED = (
    "packages/desk-ml/src/*", "packages/boss/src/*", "packages/desk/src/*", "packages/analysts/src/*",
    "packages/risk-engine/src/*", "packages/ledger/src/*", "packages/brokers/src/*", "packages/backtest/src/*",
    "config/risk_limits*.yaml", "config/analysts.yaml", "config/charges.yaml", "config/event_path.yaml",
    "tools/backtest_gate/fixtures/*", EXPECTED_REL,
)
FIELDS = {"oos": "OOS results", "costs": "Costs", "dsr": "DSR", "trials": "Trial count"}
NEEDS_NUMBER = ("dsr", "trials")
_NA = re.compile(r"^n/?a\b[\s:—–-]*(.*)$", re.I)


def gated(changed: Sequence[str]) -> list[str]:
    return [p for p in changed if any(fnmatch.fnmatch(p, g) for g in GATED)]


def section(body: str) -> Optional[str]:
    body = re.sub(r"<!--.*?-->", "", body or "", flags=re.S)
    m = re.search(r"^#{2,3}\s*honest[ -]backtest\b.*?$(.*?)(?=^#{1,3}\s|\Z)", body, re.I | re.M | re.S)
    return m.group(1) if m else None


def field_values(text: str) -> dict[str, str]:
    out = {}
    for key, label in FIELDS.items():
        m = re.search(rf"{re.escape(label)}\s*(?:\*\*)?\s*:\s*(?:\*\*)?(.*)$", text, re.I | re.M)
        out[key] = (m.group(1).strip() if m else "")
    return out


def check(body: str, changed: Sequence[str]) -> list[str]:
    hits = gated(changed)
    if not hits:
        return []
    moved = EXPECTED_REL in changed
    text = section(body)
    why = f"gated paths changed ({', '.join(hits[:5])}{' …' if len(hits) > 5 else ''})"
    if text is None:
        return [f"{why}: the PR body needs a '## Honest backtest' section (see .github/pull_request_template.md)"]
    problems = []
    for key, value in field_values(text).items():
        label = FIELDS[key]
        if not value or re.fullmatch(r"(<[^>]*>|todo|tbd|\?|-|…|\.\.\.)", value, re.I):
            problems.append(f"'{label}' is empty")
            continue
        na = _NA.match(value)
        if na:
            if moved:
                problems.append(f"'{label}' cannot be N/A: expected_results.json changed, so results moved")
            elif len(na.group(1).strip()) < 10:
                problems.append(f"'{label}' is N/A without a reason (write 'N/A: <why>')")
            continue
        if key in NEEDS_NUMBER and not re.search(r"\d", value):
            problems.append(f"'{label}' needs a number (got {value[:40]!r})")
    return [f"{why}: {p}" for p in problems]


def changed_files(base: str, head: str) -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", f"{base}...{head}"], check=True, capture_output=True, text=True)
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="tools/backtest_gate/pr_check.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--body-file", type=Path, help="PR body (default: pull_request.body from $GITHUB_EVENT_PATH)")
    ap.add_argument("--changed", nargs="*", help="changed paths (default: git diff --name-only base...head)")
    ap.add_argument("--base")
    ap.add_argument("--head", default="HEAD")
    args = ap.parse_args(argv)

    if args.body_file:
        body = args.body_file.read_text(encoding="utf-8")
    else:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        body = ((event.get("pull_request") or {}).get("body")) or ""
    if args.changed is not None:
        changed = args.changed
    elif args.base:
        changed = changed_files(args.base, args.head)
    else:
        ap.error("pass --changed or --base")
    problems = check(body, changed)
    if not problems:
        hits = gated(changed)
        print(f"PASS: honest-backtest check ({len(hits)} gated path(s) changed)")
        return 0
    print("FAIL: honest-backtest section incomplete")
    for p in problems:
        print(f"  {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
