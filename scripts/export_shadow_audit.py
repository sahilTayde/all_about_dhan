#!/usr/bin/env python3
"""Export shadow ANALYST_VOTE rows: one CSV row per session, minute and underlying.

    python scripts/export_shadow_audit.py --audit path/to/events.sqlite --out shadow.csv

Paper only. Reads the append-only events table. Does not call a broker.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "packages" / "analysts" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from analysts.shadow_export import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
