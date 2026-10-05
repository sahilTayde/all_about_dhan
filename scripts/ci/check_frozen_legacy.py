#!/usr/bin/env python3
"""Check frozen legacy manifest: editing any frozen file fails CI.

Exit 0 if all files match the manifest, 1 otherwise.

Optional argv[1] is the input being checked so the failure message cites the
right baseline: committed golden 12 / +69,309.10, tape 63 / -96,190.79.
"""

import hashlib
import sys
from pathlib import Path

COMMITTED_GOLDEN = "12 / +69,309.10"
TAPE_BASELINE = "63 / -96,190.79"


def baseline_for(input_path: str | None) -> str:
    """Cite the committed golden unless the input is a recorder tape."""
    if input_path is None:
        return COMMITTED_GOLDEN
    name = input_path.replace("\\", "/").lower()
    if "synthetic_session" in name or "/fixtures/" in name:
        return COMMITTED_GOLDEN
    if (
        name.endswith(".jsonl")
        or "dual-tape" in name
        or "/recon/" in name
        or "/tape" in name
    ):
        return TAPE_BASELINE
    return COMMITTED_GOLDEN


def main(argv: list[str] | None = None) -> int:
    """Check frozen legacy manifest."""
    args = list(sys.argv[1:] if argv is None else argv)
    input_path = args[0] if args else None
    repo_root = Path(__file__).resolve().parents[2]
    manifest_path = repo_root / "config" / "legacy_frozen.sha256"

    if not manifest_path.exists():
        print(f"Error: manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    # Parse manifest
    expected: dict[str, str] = {}
    for line in manifest_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        expected[parts[1]] = parts[0]

    if not expected:
        print("Error: empty manifest", file=sys.stderr)
        return 1

    # Check each file
    mismatches: list[str] = []
    for rel_path, expected_hash in sorted(expected.items()):
        file_path = repo_root / rel_path
        if not file_path.exists():
            print(f"MISSING: {rel_path}", file=sys.stderr)
            mismatches.append(rel_path)
            continue

        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            print(f"MISMATCH: {rel_path}", file=sys.stderr)
            print(f"  expected: {expected_hash}", file=sys.stderr)
            print(f"    actual: {actual_hash}", file=sys.stderr)
            mismatches.append(rel_path)

    if mismatches:
        print(
            f"\nFrozen legacy check failed: {len(mismatches)} file(s) modified",
            file=sys.stderr,
        )
        print(
            f"Editing frozen files breaks the legacy baseline ({baseline_for(input_path)})",
            file=sys.stderr,
        )
        return 1

    print(f"Frozen legacy check passed: {len(expected)} files unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
