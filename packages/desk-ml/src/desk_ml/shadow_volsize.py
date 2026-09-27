"""VOLSIZE-7B shadow lot size. Log only.

shadow lots = clip(round(25 * 27.4 / EM30), 5, 25), where EM30 is the S1
forecast in index points. This number is never written onto an order.
"""

from __future__ import annotations

from typing import Any, Optional


def shadow_lots(em30: Optional[float]) -> Optional[int]:
    """Lots the shadow book would have used. None when EM30 is missing or not positive."""
    if em30 is None:
        return None
    try:
        em = float(em30)
    except (TypeError, ValueError):
        return None
    if em <= 0:
        return None
    raw = round(25.0 * 27.4 / em)
    return int(max(5, min(25, raw)))


def volsize_row(*, em30: Optional[float], live_lots: Optional[int]) -> dict[str, Any]:
    lots = shadow_lots(em30)
    live = None
    if live_lots is not None:
        try:
            live = int(live_lots)
        except (TypeError, ValueError):
            live = None
    return {"shadow_lots": lots, "live_lots": live, "em30": em30}
