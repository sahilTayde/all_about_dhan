#!/usr/bin/env python3
"""Check frozen legacy manifest: editing any frozen file fails CI.

Exit 0 if all files match the manifest, 1 otherwise.
"""

import hashlib
import sys
from pathlib import Path


def main() -> int:
    """Check frozen legacy manifest."""
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
        print(f"\nFrozen legacy check failed: {len(mismatches)} file(s) modified", file=sys.stderr)
        print("Editing frozen files breaks the legacy baseline (NIFTY 63/-96,190.79)", file=sys.stderr)
        return 1

    print(f"Frozen legacy check passed: {len(expected)} files unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
