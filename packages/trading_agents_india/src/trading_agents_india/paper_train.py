"""Founder paper-train gate: record tickets for ML; never live Dhan orders.

PAPER_TRAIN_NO_DENY=1 (or --paper-train) books paper CE/PE even when the
dealer/overlay would HOLD. Production live deny stays off this flag.
STALE / WRONG_STRIKE / missing prints still cannot invent a fill.
"""

from __future__ import annotations

import os
from typing import Optional


def paper_train_no_deny(explicit: Optional[bool] = None) -> bool:
    if explicit is True:
        return True
    if explicit is False:
        return False
    raw = os.environ.get("PAPER_TRAIN_NO_DENY", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}
