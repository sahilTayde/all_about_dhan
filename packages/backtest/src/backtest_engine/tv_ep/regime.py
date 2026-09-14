"""Simple TREND vs RANGE split. Documented PROJECT rule — not a Dhan field."""

from __future__ import annotations

from backtest_engine.indicators import Bar, sma

# |SMA50 now − SMA50 lookback| / close ≥ this → TREND. Else RANGE.
SLOPE_FRAC = 0.002
SMA_LEN = 50
LOOKBACK = 10


def regime_labels(bars: list[Bar]) -> list[str]:
    """Label each bar TREND / RANGE / UNKNOWN.

    TREND: 50-SMA has moved at least SLOPE_FRAC of price over LOOKBACK bars.
    RANGE: SMA is defined but slope is flatter.
    UNKNOWN: warmup (not enough bars for SMA50 + lookback).
    """
    closes = [b.close for b in bars]
    mid = sma(closes, SMA_LEN)
    out: list[str] = []
    for i, bar in enumerate(bars):
        j = i - LOOKBACK
        if j < 0 or mid[i] is None or mid[j] is None or bar.close <= 0:
            out.append("UNKNOWN")
            continue
        slope = abs(float(mid[i]) - float(mid[j])) / bar.close
        out.append("TREND" if slope >= SLOPE_FRAC else "RANGE")
    return out


def regime_doc() -> dict[str, object]:
    return {
        "rule": "TREND if |SMA50(t)−SMA50(t-10)| / close ≥ 0.002 else RANGE",
        "sma_len": SMA_LEN,
        "lookback_bars": LOOKBACK,
        "slope_frac": SLOPE_FRAC,
        "layer": "HYPOTHESIS",
        "note": "Not ADX. Not a Dhan series. Split trades by entry-bar label only.",
    }
