#!/usr/bin/env python3
"""Hygiene gate for a PUBLIC repo: secrets, large files, data payloads, private info in fixtures.

Scans every tracked file (``git ls-files``). Fails on:
- a secret-looking value (private keys, cloud/API tokens, JWTs, Dhan credential assignments);
- a file over 2 MB;
- data payloads outside test fixtures (``data/**/*.jsonl``, ``*.sqlite``, ``*.parquet``, tapes);
- Mac home paths, e-mail addresses, broker order ids or DHAN_ strings in fixtures and goldens.
Values are never printed, only the file, line and rule.
"""

from __future__ import annotations

import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 2 * 1024 * 1024
SECRET_RULES = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "slack_token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
    "telegram_bot_token": re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_-]{33}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}"),
    "dhan_credential": re.compile(
        r"DHAN_(?:ACCESS_TOKEN|CLIENT_SECRET|REFRESH_TOKEN|API_SECRET)\s*[=:]\s*['\"]?(?!your_)[A-Za-z0-9._-]{16,}"
    ),
}
# (path, rule) pairs that are known fakes. Keep this list short and explained.
ALLOW = {
    ("packages/docs-auditor/tests/test_docs_auditor.py", "dhan_credential"),  # fake token proving the auditor redacts
}
DATA_PAYLOADS = ("data/**/*.jsonl", "*.sqlite", "*.parquet", "*.feather", "data/tape/*", "*DUAL-TAPE*")
# Tracked before PR-A and small; the derived agent_rag knowledge base is committed on purpose.
DATA_ALLOW = {"data/knowledge/agent_rag.sqlite"}
FIXTURE_GLOBS = ("packages/*/tests/fixtures/*", "packages/*/tests/golden/*")
PRIVATE_IN_FIXTURES = {
    "mac_home_path": re.compile(r"/Users/[A-Za-z]"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "dhan_string": re.compile(r"DHAN_[A-Z]"),
    "broker_order_id": re.compile(r"\b(?:orderId|order_id|dhanClientId)\b"),
}


def tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [p for p in out.decode().split("\0") if p]


def self_test() -> None:
    """Each rule fires on a synthetic sample and stays quiet on the placeholders the repo uses."""
    samples = {
        "private_key": "-----BEGIN RSA PRIVATE KEY-----", "aws_access_key": "AKIA" + "ABCDEFGHIJKLMNOP",
        "github_token": "ghp_" + "a" * 36, "openai_key": "sk-" + "A1" * 20, "slack_token": "xoxb-1234567890-abc",
        "jwt": "eyJ" + "a" * 20 + ".eyJ" + "b" * 20 + "." + "c" * 12,
        "dhan_credential": "DHAN_ACCESS_TOKEN=" + "Z" * 30, "telegram_bot_token": "123456789:AA" + "x" * 33,
    }
    for rule, text in samples.items():
        assert SECRET_RULES[rule].search(text), rule
    for quiet in ("DHAN_ACCESS_TOKEN=", 'export DHAN_ACCESS_TOKEN="your_access_token"', "sk-short"):
        assert not any(rx.search(quiet) for rx in SECRET_RULES.values()), quiet
    assert fnmatch("data/tape/2026-09-25.jsonl", DATA_PAYLOADS[0]) and fnmatch("x/y.sqlite", "*.sqlite")
    assert PRIVATE_IN_FIXTURES["mac_home_path"].search('"/Users/sahil/x"')
    print("scan_repo self-test OK")


def main() -> int:
    if "--self-test" in sys.argv:
        self_test()
        return 0
    problems: list[str] = []
    for rel in tracked():
        path = ROOT / rel
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > MAX_BYTES:
            problems.append(f"{rel}: {size / 1e6:.1f} MB > 2 MB")
        is_fixture = any(fnmatch(rel, g) for g in FIXTURE_GLOBS)
        if rel not in DATA_ALLOW and not is_fixture and any(fnmatch(rel, g) for g in DATA_PAYLOADS):
            problems.append(f"{rel}: data payload outside test fixtures")
        if size > MAX_BYTES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for rule, rx in SECRET_RULES.items():
                if (rel, rule) not in ALLOW and rx.search(line):
                    problems.append(f"{rel}:{n}: looks like a secret ({rule})")
            if is_fixture:
                for rule, rx in PRIVATE_IN_FIXTURES.items():
                    if rx.search(line):
                        problems.append(f"{rel}:{n}: private data in a fixture ({rule})")
    for p in problems:
        print(f"HYGIENE: {p}")
    print(f"hygiene: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
