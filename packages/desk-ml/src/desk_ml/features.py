"""Compact 1m INDEX+CE+PE features. ml001-v1 vectors stay returns-only.

Greeks/IV live on Triple.wing_quotes for the paper overlay (strike/stop/target).
Never invent prints or greeks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

FEATURE_SET_VERSION = "ml001-v1"
FEATURE_NAMES = (
    "idx_ret",
    "ce_ret",
    "pe_ret",
    "spread_chg",
    "abs_residual",
)

EPS = 1e-9


@dataclass(frozen=True)
class Triple:
    ts: int
    idx_close: float
    ce_close: float
    pe_close: float
    atm_strike: Optional[float] = None
    ce_low: Optional[float] = None
    pe_low: Optional[float] = None
    itm_ce_close: Optional[float] = None
    itm_pe_close: Optional[float] = None
    itm_ce_strike: Optional[float] = None
    itm_pe_strike: Optional[float] = None
    itm_ce_low: Optional[float] = None
    itm_pe_low: Optional[float] = None
    wing_quotes: Optional[dict] = None
    idx_volume: Optional[float] = None


def _ret(prev: float, cur: float) -> Optional[float]:
    if prev is None or cur is None:
        return None
    if abs(prev) < EPS:
        return None
    return (cur - prev) / abs(prev)


def build_feature_rows(triples: Sequence[Triple]) -> list[dict]:
    ordered = sorted(triples, key=lambda t: t.ts)
    rows: list[dict] = []
    prev: Optional[Triple] = None
    for bar in ordered:
        if prev is None:
            prev = bar
            continue
        idx_ret = _ret(prev.idx_close, bar.idx_close)
        ce_ret = _ret(prev.ce_close, bar.ce_close)
        pe_ret = _ret(prev.pe_close, bar.pe_close)
        if idx_ret is None or ce_ret is None or pe_ret is None:
            prev = bar
            continue
        prev_spread = prev.ce_close - prev.pe_close
        spread = bar.ce_close - bar.pe_close
        denom = abs(prev_spread) if abs(prev_spread) > EPS else max(abs(prev.ce_close), abs(prev.pe_close), 1.0)
        spread_chg = (spread - prev_spread) / denom
        premium_move = 0.5 * (abs(ce_ret) + abs(pe_ret))
        abs_residual = abs(idx_ret) - premium_move
        rows.append(
            {
                "ts": bar.ts,
                "idx_ret": float(idx_ret),
                "ce_ret": float(ce_ret),
                "pe_ret": float(pe_ret),
                "spread_chg": float(spread_chg),
                "abs_residual": float(abs_residual),
                "idx_close": bar.idx_close,
                "ce_close": bar.ce_close,
                "pe_close": bar.pe_close,
            }
        )
        prev = bar
    return rows


def vectors_from_rows(rows: Iterable[dict]) -> list[list[float]]:
    return [[float(row[name]) for name in FEATURE_NAMES] for row in rows]
