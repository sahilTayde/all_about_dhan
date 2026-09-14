"""Frozen PAPER champions for Tuesday ITM option watch — NO_PROMOTE, no live orders.

Remembered from Aug–Sep 2026 strike sweep + VWAP-assumed variants + Flawless Victory
(Bunghole MPL-2.0 Pine) grid winners on option premium.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from backtest_engine.flawless_victory import FlawlessParams, flawless_signals
from backtest_engine.indicators import (
    Bar,
    ema,
    rsi,
    session_vwap,
    session_vwap_of,
    sma,
    supertrend,
    wma,
)
from backtest_engine.run_itm_lab import bollinger


SignalFn = Callable[[list[Bar]], tuple[list[bool], list[bool]]]


@dataclass(frozen=True)
class Champion:
    id: str
    name: str
    family: str
    tf_minutes: int  # 1, 5, 10, 15, …
    plain_english: str
    why_remembered: str
    sl: Optional[float]
    tp: Optional[float]
    prefer_side: str  # PE | CE | BOTH
    signals: SignalFn


def _bb_20_25(bars: list[Bar]) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in bars]
    lo, mid, _ = bollinger(c, 20, 2.5)
    rv = rsi(c, 14)
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        if None in (lo[i], lo[i - 1], mid[i], rv[i]):
            continue
        entry[i] = c[i - 1] <= lo[i - 1] and c[i] > lo[i]
        exit_[i] = c[i] >= mid[i] or rv[i] >= 55
    return entry, exit_


def _ema_st_5m(bars: list[Bar]) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in bars]
    f, s = ema(c, 9), ema(c, 21)
    st = supertrend(bars, 10, 3.0)
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        if None in (f[i], s[i], f[i - 1], s[i - 1], st[i]):
            continue
        cross_up = f[i - 1] <= s[i - 1] and f[i] > s[i]
        cross_dn = f[i - 1] >= s[i - 1] and f[i] < s[i]
        entry[i] = cross_up and c[i] > st[i]
        exit_[i] = cross_dn or c[i] < st[i]
    return entry, exit_


def _ema_st_vwap_5m(bars: list[Bar]) -> tuple[list[bool], list[bool]]:
    """Lab winner + session VWAP filter (volume when present, else equal-weight assume)."""
    entry, exit_ = _ema_st_5m(bars)
    c = [b.close for b in bars]
    vw = session_vwap(bars, equal_weight_if_no_volume=True)
    out_e = [False] * len(bars)
    for i in range(len(bars)):
        if entry[i] and vw[i] is not None and c[i] > vw[i]:
            out_e[i] = True
    return out_e, exit_


def _sma_cross_sltp(bars: list[Bar]) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in bars]
    f, s = sma(c, 10), sma(c, 50)
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        if None in (f[i], s[i], f[i - 1], s[i - 1]):
            continue
        entry[i] = f[i - 1] <= s[i - 1] and f[i] > s[i]
        exit_[i] = f[i - 1] >= s[i - 1] and f[i] < s[i]
    return entry, exit_


def _vwap_rsi_cross(bars: list[Bar]) -> tuple[list[bool], list[bool]]:
    """Pine-style: session VWAP + EMA3×WMA21 cross + RSI — assumed VWAP ready for live."""
    c = [b.close for b in bars]
    rv, ef, ws, eb = rsi(c, 14), ema(c, 3), wma(c, 21), ema(c, 21)
    vw = session_vwap_of(bars, c, equal_weight_if_no_volume=True)
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        if None in (rv[i], ef[i], ws[i], eb[i], vw[i], ef[i - 1], ws[i - 1]):
            continue
        cross_up = ef[i - 1] <= ws[i - 1] and ef[i] > ws[i]
        cross_dn = ef[i - 1] >= ws[i - 1] and ef[i] < ws[i]
        entry[i] = c[i] > vw[i] and rv[i] >= 60 and c[i] > eb[i] and cross_up
        exit_[i] = cross_dn or rv[i] < 55
    return entry, exit_


def _ema_cross_vwap(bars: list[Bar]) -> tuple[list[bool], list[bool]]:
    c = [b.close for b in bars]
    f, s = ema(c, 9), ema(c, 21)
    vw = session_vwap(bars, equal_weight_if_no_volume=True)
    entry = [False] * len(bars)
    exit_ = [False] * len(bars)
    for i in range(1, len(bars)):
        if None in (f[i], s[i], f[i - 1], s[i - 1], vw[i]):
            continue
        cross_up = f[i - 1] <= s[i - 1] and f[i] > s[i]
        cross_dn = f[i - 1] >= s[i - 1] and f[i] < s[i]
        entry[i] = cross_up and c[i] > vw[i]
        exit_[i] = cross_dn or c[i] < vw[i]
    return entry, exit_


def _fv(params: FlawlessParams) -> SignalFn:
    def _signals(bars: list[Bar]) -> tuple[list[bool], list[bool]]:
        return flawless_signals(bars, params)

    return _signals


# Flawless Victory grid winners (v1 only — Pine v2/v3 defaults bled on premium)
_FV_V1_10M_BB15 = FlawlessParams("v1", bb_length=20, bb_mult=1.5, rsi_buy=42, rsi_sell=70)
_FV_V1_5M_BB20 = FlawlessParams("v1", bb_length=20, bb_mult=2.0, rsi_buy=42, rsi_sell=70)
_FV_V1_10M_BB20 = FlawlessParams("v1", bb_length=20, bb_mult=2.0, rsi_buy=42, rsi_sell=70)
_FV_V1_1M_RSI60 = FlawlessParams("v1", bb_length=20, bb_mult=1.0, rsi_buy=42, rsi_sell=60)
_FV_V1_15M_BB17 = FlawlessParams("v1", bb_length=17, bb_mult=1.0, rsi_buy=42, rsi_sell=70)


CHAMPIONS: list[Champion] = [
    Champion(
        id="MIX-CHAMP-EMA-ST-5M",
        name="EMA×ST (lab winner)",
        family="EMA_ST",
        tf_minutes=5,
        plain_english=(
            "5m: buy when EMA9 crosses above EMA21 and price > Supertrend(10,3); "
            "exit on EMA cross down or close below Supertrend."
        ),
        why_remembered="Best aggregate after-cost on 10 ITM PE+CE Aug–Sep sweep (~41% WR).",
        sl=None,
        tp=None,
        prefer_side="PE",
        signals=_ema_st_5m,
    ),
    Champion(
        id="MIX-CHAMP-EMA-ST-VWAP-5M",
        name="EMA×ST + VWAP filter",
        family="EMA_ST_VWAP",
        tf_minutes=5,
        plain_english=(
            "Same as EMA×ST, but only enter when premium is above session VWAP "
            "(volume-weighted; equal-weight assume if vol=0)."
        ),
        why_remembered="Tuesday-ready: live session VWAP should tighten entries vs lab.",
        sl=None,
        tp=None,
        prefer_side="PE",
        signals=_ema_st_vwap_5m,
    ),
    Champion(
        id="MIX-CHAMP-SMA-CROSS-5M",
        name="SMA10×50 + SL/TP",
        family="SMA_CROSS",
        tf_minutes=5,
        plain_english="5m: SMA10 crosses above SMA50; exit on cross down or 15% SL / 30% TP.",
        why_remembered="Runner-up on strike sweep; most contracts positive (12/20).",
        sl=0.15,
        tp=0.30,
        prefer_side="BOTH",
        signals=_sma_cross_sltp,
    ),
    Champion(
        id="MIX-CHAMP-VWAP-RSI-5M",
        name="VWAP + RSI cross (Pine)",
        family="VWAP_RSI",
        tf_minutes=5,
        plain_english=(
            "5m: price > session VWAP, RSI≥60, above EMA21, EMA3×WMA21 cross up; "
            "exit cross down or RSI<55. SL20%/TP40%."
        ),
        why_remembered="Founder Pine path — needs live VWAP; assumed VWAP used in offline lab.",
        sl=0.20,
        tp=0.40,
        prefer_side="BOTH",
        signals=_vwap_rsi_cross,
    ),
    Champion(
        id="MIX-CHAMP-EMA-VWAP-5M",
        name="EMA9×21 + VWAP",
        family="EMA_VWAP",
        tf_minutes=5,
        plain_english="5m: EMA9×21 cross with price above session VWAP; exit below VWAP or cross down.",
        why_remembered="Simple VWAP-gated trend for live paper comparison.",
        sl=None,
        tp=None,
        prefer_side="PE",
        signals=_ema_cross_vwap,
    ),
    Champion(
        id="MIX-CHAMP-BB-5M",
        name="BB mean-revert",
        family="BB",
        tf_minutes=5,
        plain_english="5m: bounce off lower Bollinger(20,2.5); exit mid-band or RSI≥55.",
        why_remembered="High win-rate on single-strike lab; lost across strike sweep — challenger.",
        sl=None,
        tp=None,
        prefer_side="BOTH",
        signals=_bb_20_25,
    ),
    # --- Flawless Victory (Bunghole) — grid winners only; v2/v3 Pine defaults NOT boarded ---
    Champion(
        id="MIX-CHAMP-FV-V1-10M-BB15",
        name="Flawless v1 · 10m BB×1.5",
        family="FLAWLESS_V1",
        tf_minutes=10,
        plain_english=(
            "10m Flawless v1: buy close < BB lower(20,1.5) and RSI>42; "
            "sell close > BB upper and RSI>70. No SL/TP."
        ),
        why_remembered="Top Flawless grid cell on ITM premiums (~79% succ, PE-biased).",
        sl=None,
        tp=None,
        prefer_side="PE",
        signals=_fv(_FV_V1_10M_BB15),
    ),
    Champion(
        id="MIX-CHAMP-FV-V1-5M-BB20",
        name="Flawless v1 · 5m BB×2.0",
        family="FLAWLESS_V1",
        tf_minutes=5,
        plain_english=(
            "5m Flawless v1: BB(20,2.0) + RSI>42 entry; BB upper + RSI>70 exit. No SL/TP."
        ),
        why_remembered="Best 5m Flawless cell after costs on premium watch set.",
        sl=None,
        tp=None,
        prefer_side="PE",
        signals=_fv(_FV_V1_5M_BB20),
    ),
    Champion(
        id="MIX-CHAMP-FV-V1-10M-BB20",
        name="Flawless v1 · 10m BB×2.0",
        family="FLAWLESS_V1",
        tf_minutes=10,
        plain_english=(
            "10m Flawless v1: BB(20,2.0) + RSI>42 entry; BB upper + RSI>70 exit. No SL/TP."
        ),
        why_remembered="Wider-band 10m Flawless companion (high succ %, fewer trades).",
        sl=None,
        tp=None,
        prefer_side="PE",
        signals=_fv(_FV_V1_10M_BB20),
    ),
    Champion(
        id="MIX-CHAMP-FV-V1-1M-RSI60",
        name="Flawless v1 · 1m early RSI exit",
        family="FLAWLESS_V1",
        tf_minutes=1,
        plain_english=(
            "1m Flawless v1: BB(20,1) + RSI>42 entry; exit BB upper + RSI>60 (earlier than Pine 70)."
        ),
        why_remembered="Only 1m Flawless cell green after costs on watch set.",
        sl=None,
        tp=None,
        prefer_side="PE",
        signals=_fv(_FV_V1_1M_RSI60),
    ),
    Champion(
        id="MIX-CHAMP-FV-V1-15M-BB17",
        name="Flawless v1 · 15m BB17",
        family="FLAWLESS_V1",
        tf_minutes=15,
        plain_english=(
            "15m Flawless v1: BB(17,1) + RSI>42 entry; BB upper + RSI>70 exit. No SL/TP."
        ),
        why_remembered="Best 15m Flawless cell (modest +₹); slow TF for paper watch.",
        sl=None,
        tp=None,
        prefer_side="PE",
        signals=_fv(_FV_V1_15M_BB17),
    ),
]


def champion_by_id(champ_id: str) -> Champion:
    for c in CHAMPIONS:
        if c.id == champ_id:
            return c
    raise KeyError(champ_id)


def champions_meta() -> list[dict[str, Any]]:
    return [
        {
            "id": c.id,
            "name": c.name,
            "family": c.family,
            "tf_minutes": c.tf_minutes,
            "plain_english": c.plain_english,
            "why_remembered": c.why_remembered,
            "sl": c.sl,
            "tp": c.tp,
            "prefer_side": c.prefer_side,
            "promotion": "NO_PROMOTE",
            "orders": "refused",
        }
        for c in CHAMPIONS
    ]
