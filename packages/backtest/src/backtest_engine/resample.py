"""Resample HQ 1m bars to spoken TFs that are not in the HQ enum (2m, 3m)."""

from __future__ import annotations

from backtest_engine.indicators import Bar


def resample(bars: list[Bar], minutes: int) -> list[Bar]:
    if minutes <= 1:
        return list(bars)
    bucket = minutes * 60
    groups: dict[int, list[Bar]] = {}
    order: list[int] = []
    for bar in bars:
        key = (bar.ts // bucket) * bucket
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(bar)
    out: list[Bar] = []
    for key in order:
        chunk = groups[key]
        out.append(
            Bar(
                ts=key,
                open=chunk[0].open,
                high=max(b.high for b in chunk),
                low=min(b.low for b in chunk),
                close=chunk[-1].close,
                volume=sum(b.volume for b in chunk),
            )
        )
    return out
