"""OI_CADENCE: how often OI actually changes, per instrument, over minute-aligned windows.

The first observation of an instrument is a baseline, not a change. A window is reported
only if the instrument was already observed when it started. Gaps are measured between
changes inside the window (changes at 10, 25, 55 s -> 3 updates, gaps 15 and 30,
median 22.5; p90 uses inclusive linear interpolation).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from marketdata.clock import IST, iso


@dataclass
class _State:
    first_seen_s: float
    last_oi: int
    last_change_s: float | None = None
    changes: list[float] = field(default_factory=list)
    sources: set[str] = field(default_factory=set)


def _p90(gaps: list[float]) -> float:
    if len(gaps) == 1:
        return gaps[0]
    return statistics.quantiles(gaps, n=10, method="inclusive")[8]


class OiCadenceTracker:
    def __init__(self, window_s: int = 60) -> None:
        self.window_s = window_s
        self._state: dict[str, _State] = {}

    def observe(self, iid: str, oi: int, t: float, source: str) -> None:
        state = self._state.get(iid)
        if state is None:
            self._state[iid] = _State(first_seen_s=t, last_oi=oi, sources={source})
            return
        state.sources.add(source)
        if oi != state.last_oi:
            state.last_oi = oi
            state.changes.append(t)

    def close_window(self, end_s: float) -> list[dict[str, Any]]:
        """OI_CADENCE payloads for the window [end_s - window_s, end_s)."""
        start = end_s - self.window_s
        out: list[dict[str, Any]] = []
        for iid, state in self._state.items():
            before = [c for c in state.changes if c < end_s]
            inside = [c for c in before if c >= start]
            state.changes = state.changes[len(before) :]
            if before:
                state.last_change_s = before[-1]
            if state.first_seen_s > start:
                continue
            gaps = [b - a for a, b in zip(inside, inside[1:], strict=False)]
            last = state.last_change_s
            out.append(
                {
                    "instrument_id": iid,
                    "window_s": self.window_s,
                    "oi_updates": len(inside),
                    "median_gap_s": round(statistics.median(gaps), 3) if gaps else None,
                    "p90_gap_s": round(_p90(gaps), 3) if gaps else None,
                    "last_oi_change": iso(datetime.fromtimestamp(last, IST)) if last is not None else None,
                    "sources": sorted(state.sources),
                }
            )
        return out

    def drop(self, iid: str) -> None:
        self._state.pop(iid, None)
