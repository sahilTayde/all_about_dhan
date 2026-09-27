#!/usr/bin/env python3
"""CI entry for V2-06 K9 strategy onboarding. Paper only; no secrets."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = ROOT / "packages" / "strategies" / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from strategies.onboarding import main

if __name__ == "__main__":
    raise SystemExit(main())
