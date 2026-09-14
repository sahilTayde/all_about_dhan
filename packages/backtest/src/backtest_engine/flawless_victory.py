"""Flawless Victory (© Bunghole, MPL-2.0 Pine) — long-only BB+RSI/MFI on option premium.

PAPER port. NO_PROMOTE. Not identical to TV fills (next-bar open).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from backtest_engine.indicators import Bar, rsi, sma


def mfi(bars: list[Bar], length: int = 14) -> list[float | None]:
    """Money Flow Index (TradingView-style on hlc3 + volume)."""
    n = len(bars)
    out: list[float | None] = [None] * n
    if n < length + 1:
        return out
    tp = [(b.high + b.low + b.close) / 3.0 for b in bars]
    for i in range(length, n):
        pos = 0.0
        neg = 0.0
        for j in range(i - length + 1, i + 1):
            # Pine: upper = vol * (change <= 0 ? 0 : tp); lower = vol * (change >= 0 ? 0 : tp)
            ch = tp[j] - tp[j - 1]
            raw = bars[j].volume * tp[j]
            if ch > 0:
                pos += raw
            elif ch < 0:
                neg += raw
            # ch == 0 → neither bucket
        if neg == 0:
            out[i] = 100.0
        elif pos == 0:
            out[i] = 0.0
        else:
            out[i] = 100.0 - (100.0 / (1.0 + pos / neg))
    return out


def bollinger_tv(
    closes: list[float], length: int, mult: float
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """SMA basis + population-style stdev like Pine ta.stdev (sample ddof=0)."""
    mid = sma(closes, length)
    upper: list[float | None] = []
    lower: list[float | None] = []
    for i in range(len(closes)):
        if mid[i] is None:
            upper.append(None)
            lower.append(None)
            continue
        window = closes[i + 1 - length : i + 1]
        mean = mid[i]
        var = sum((x - mean) ** 2 for x in window) / length
        sd = math.sqrt(var)
        upper.append(mean + mult * sd)
        lower.append(mean - mult * sd)
    return lower, mid, upper


@dataclass(frozen=True)
class FlawlessParams:
    version: str  # v1 | v2 | v3
    bb_length: int = 20
    bb_mult: float = 1.0
    rsi_buy: float = 42.0
    rsi_sell: float = 70.0
    mfi_buy: float = 60.0  # enter when mfi < this (v3)
    mfi_sell: float = 64.0  # exit when mfi > this (v3)
    sl: Optional[float] = None
    tp: Optional[float] = None

    def label(self) -> str:
        sl = f"SL{self.sl*100:.2f}" if self.sl else "noSL"
        tp = f"TP{self.tp*100:.2f}" if self.tp else "noTP"
        return (
            f"{self.version}|BB{self.bb_length}x{self.bb_mult}|"
            f"RSI{self.rsi_buy}/{self.rsi_sell}|MFI{self.mfi_buy}/{self.mfi_sell}|{sl}/{tp}"
        )


def flawless_signals(
    bars: list[Bar], params: FlawlessParams
) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in bars]
    lo, _, hi = bollinger_tv(c, params.bb_length, params.bb_mult)
    rv = rsi(c, 14)
    mf = mfi(bars, 14) if params.version == "v3" else [None] * len(bars)
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(len(bars)):
        if lo[i] is None or hi[i] is None or rv[i] is None:
            continue
        bb_buy = c[i] < lo[i]
        bb_sell = c[i] > hi[i]
        if params.version == "v1":
            entry[i] = bb_buy and rv[i] > params.rsi_buy
            exit_[i] = bb_sell and rv[i] > params.rsi_sell
        elif params.version == "v2":
            entry[i] = bb_buy and rv[i] > params.rsi_buy
            exit_[i] = bb_sell and rv[i] > params.rsi_sell
        elif params.version == "v3":
            if mf[i] is None:
                continue
            entry[i] = bb_buy and mf[i] < params.mfi_buy
            exit_[i] = bb_sell and rv[i] > params.rsi_sell and mf[i] > params.mfi_sell
        else:
            raise ValueError(params.version)
    return entry, exit_


# Pine defaults + compact permutation grid
def default_param_grid() -> list[FlawlessParams]:
    grid: list[FlawlessParams] = [
        # Exact Pine defaults
        FlawlessParams("v1", 20, 1.0, 42, 70, sl=None, tp=None),
        FlawlessParams("v2", 17, 1.0, 42, 76, sl=0.06604, tp=0.02328),
        FlawlessParams(
            "v3", 20, 1.0, 42, 65, mfi_buy=60, mfi_sell=64, sl=0.08882, tp=0.02317
        ),
        # BB mult / length ablations (v1-style, no SL)
        FlawlessParams("v1", 20, 1.5, 42, 70),
        FlawlessParams("v1", 20, 2.0, 42, 70),
        FlawlessParams("v1", 17, 1.0, 42, 70),
        FlawlessParams("v1", 25, 1.0, 42, 70),
        FlawlessParams("v1", 20, 1.0, 30, 70),
        FlawlessParams("v1", 20, 1.0, 42, 60),
        FlawlessParams("v1", 20, 1.0, 50, 70),
        # v2 SL/TP permutations
        FlawlessParams("v2", 17, 1.0, 42, 76, sl=0.05, tp=0.02),
        FlawlessParams("v2", 17, 1.0, 42, 76, sl=0.10, tp=0.05),
        FlawlessParams("v2", 17, 1.0, 42, 76, sl=0.15, tp=0.30),
        FlawlessParams("v2", 20, 1.5, 42, 76, sl=0.06604, tp=0.02328),
        FlawlessParams("v2", 20, 2.0, 42, 70, sl=0.08, tp=0.03),
        # v3 MFI / BB / SLTP
        FlawlessParams("v3", 20, 1.0, 42, 65, 55, 64, sl=0.08882, tp=0.02317),
        FlawlessParams("v3", 20, 1.0, 42, 65, 60, 70, sl=0.08882, tp=0.02317),
        FlawlessParams("v3", 20, 1.5, 42, 65, 60, 64, sl=0.08882, tp=0.02317),
        FlawlessParams("v3", 20, 2.0, 42, 65, 60, 64, sl=0.15, tp=0.30),
        FlawlessParams("v3", 17, 1.0, 42, 65, 60, 64, sl=0.10, tp=0.05),
    ]
    return grid
