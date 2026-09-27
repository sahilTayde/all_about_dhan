"""Look-ahead harness (REG-01). Reused by later tickets.

A bar is illegal if a consumer can see it before its bucket close:
``available_ts < end`` or the event that emitted it has ``when < end``.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from marketdata.types import BarClosed, parse_ts


def lookahead_failures(emissions: Iterable[tuple[BarClosed, datetime]]) -> list[str]:
    """Return one message per emission that a consumer would see before bar end."""
    failures: list[str] = []
    for bar, when in emissions:
        end = parse_ts(bar.end)
        if when < end:
            failures.append(f"emitted at {when.isoformat()} before end {bar.end} ({bar.tf} {bar.start})")
        if bar.available_ts:
            stamped = parse_ts(bar.available_ts)
            if stamped < end:
                failures.append(f"available_ts {bar.available_ts} < end {bar.end} ({bar.tf} {bar.start})")
    return failures
