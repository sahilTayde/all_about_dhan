#!/usr/bin/env python3
"""Backtest local MRR Pine indicators on cached charts.

This is a shadow/research harness only. The source Pine files are indicators,
not strategies, so fills/exits below are explicit PROJECT assumptions.
No live orders, no promotion, no claimed customer win rate.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


IST = timezone(timedelta(hours=5, minutes=30))
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "recon"
INDEX_IDS = {
    "13": "NIFTY",
    "25": "BANKNIFTY",
    "51": "SENSEX",
}


@dataclass(frozen=True)
class Bar:
    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Trade:
    strategy_id: str
    chart_kind: str
    underlying: str
    series_key: str
    side: str
    entry_ts: int
    exit_ts: int
    entry_px: float
    exit_px: float
    points: float
    reason: str


def _clean_number(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def bars_from_chart(payload: dict[str, Any]) -> list[Bar]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    opens = data.get("open") or data.get("Open") or []
    highs = data.get("high") or data.get("High") or []
    lows = data.get("low") or data.get("Low") or []
    closes = data.get("close") or data.get("Close") or []
    vols = data.get("volume") or data.get("Volume") or []
    ts = data.get("timestamp") or data.get("time") or []
    n = min(len(opens), len(highs), len(lows), len(closes), len(ts))
    if len(vols) < n:
        vols = list(vols) + [0] * (n - len(vols))
    out: list[Bar] = []
    for i in range(n):
        try:
            out.append(
                Bar(
                    ts=int(float(ts[i])),
                    open=_clean_number(opens[i]),
                    high=_clean_number(highs[i]),
                    low=_clean_number(lows[i]),
                    close=_clean_number(closes[i]),
                    volume=_clean_number(vols[i]),
                )
            )
        except (TypeError, ValueError):
            continue
    return out


def bars_from_rolling(payload: dict[str, Any], side: str) -> list[Bar]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    block = data.get(side) if isinstance(data, dict) else None
    return bars_from_chart(block or {})


def dedupe_bars(bars: Iterable[Bar]) -> list[Bar]:
    merged: dict[int, Bar] = {}
    for bar in bars:
        if bar.open > 0 and bar.close > 0 and regular_session(bar.ts):
            merged[bar.ts] = bar
    return [merged[k] for k in sorted(merged)]


def regular_session(ts: int) -> bool:
    dt = datetime.fromtimestamp(ts, tz=IST)
    minute = dt.hour * 60 + dt.minute
    return 9 * 60 + 15 <= minute <= 15 * 60 + 30


def sma(values: list[float], length: int) -> list[float | None]:
    out: list[float | None] = []
    running = 0.0
    for i, value in enumerate(values):
        running += value
        if i >= length:
            running -= values[i - length]
        out.append(running / length if i + 1 >= length else None)
    return out


def ema(values: list[float], length: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if length <= 0 or len(values) < length:
        return out
    seed = sum(values[:length]) / length
    out[length - 1] = seed
    prev = seed
    k = 2.0 / (length + 1.0)
    for i in range(length, len(values)):
        prev = values[i] * k + prev * (1.0 - k)
        out[i] = prev
    return out


def rsi(closes: list[float], length: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) < length + 1:
        return out
    gains = 0.0
    losses = 0.0
    for i in range(1, length + 1):
        diff = closes[i] - closes[i - 1]
        gains += max(diff, 0.0)
        losses += max(-diff, 0.0)
    avg_gain = gains / length
    avg_loss = losses / length
    out[length] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for i in range(length + 1, len(closes)):
        diff = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (length - 1) + max(diff, 0.0)) / length
        avg_loss = (avg_loss * (length - 1) + max(-diff, 0.0)) / length
        out[i] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out


def wilder_atr(bars: list[Bar], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(bars)
    if len(bars) < period + 1:
        return out
    trs: list[float] = []
    for i, bar in enumerate(bars):
        if i == 0:
            trs.append(bar.high - bar.low)
        else:
            prev = bars[i - 1].close
            trs.append(max(bar.high - bar.low, abs(bar.high - prev), abs(bar.low - prev)))
    first = sum(trs[1 : period + 1]) / period
    out[period] = first
    prev_atr = first
    for i in range(period + 1, len(bars)):
        prev_atr = (prev_atr * (period - 1) + trs[i]) / period
        out[i] = prev_atr
    return out


def supertrend_direction(bars: list[Bar], period: int = 10, factor: float = 3.0) -> list[int | None]:
    """Approximate TradingView ta.supertrend direction: -1 bullish, +1 bearish."""
    atr = wilder_atr(bars, period)
    direction: list[int | None] = [None] * len(bars)
    final_upper: list[float | None] = [None] * len(bars)
    final_lower: list[float | None] = [None] * len(bars)
    supertrend: list[float | None] = [None] * len(bars)
    for i, bar in enumerate(bars):
        if atr[i] is None:
            continue
        hl2 = (bar.high + bar.low) / 2.0
        upper = hl2 + factor * atr[i]
        lower = hl2 - factor * atr[i]
        if i == 0 or final_upper[i - 1] is None or final_lower[i - 1] is None:
            final_upper[i] = upper
            final_lower[i] = lower
            direction[i] = 1
            supertrend[i] = upper
            continue
        prev_upper = final_upper[i - 1]
        prev_lower = final_lower[i - 1]
        prev_close = bars[i - 1].close
        assert prev_upper is not None and prev_lower is not None
        final_upper[i] = upper if (upper < prev_upper or prev_close > prev_upper) else prev_upper
        final_lower[i] = lower if (lower > prev_lower or prev_close < prev_lower) else prev_lower
        prev_st = supertrend[i - 1]
        if prev_st is None or prev_st == prev_upper:
            direction[i] = -1 if bar.close > final_upper[i] else 1
        else:
            direction[i] = 1 if bar.close < final_lower[i] else -1
        supertrend[i] = final_lower[i] if direction[i] == -1 else final_upper[i]
    return direction


def vwma(bars: list[Bar], length: int = 20) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(bars)):
        if i + 1 < length:
            out.append(None)
            continue
        window = bars[i + 1 - length : i + 1]
        den = sum(b.volume for b in window)
        if den <= 0:
            # PROJECT ablation for charts with no usable volume, mainly index proxy.
            out.append(sum(b.close for b in window) / length)
        else:
            out.append(sum(b.close * b.volume for b in window) / den)
    return out


def session_vwap(bars: list[Bar]) -> list[float | None]:
    out: list[float | None] = []
    last_day = None
    num = 0.0
    den = 0.0
    for bar in bars:
        day = datetime.fromtimestamp(bar.ts, tz=IST).date()
        if day != last_day:
            num = 0.0
            den = 0.0
            last_day = day
        typical = (bar.high + bar.low + bar.close) / 3.0
        weight = bar.volume if bar.volume > 0 else 1.0
        num += typical * weight
        den += weight
        out.append(num / den if den else None)
    return out


def highest(values: list[float], length: int) -> list[float | None]:
    return [max(values[i + 1 - length : i + 1]) if i + 1 >= length else None for i in range(len(values))]


def lowest(values: list[float], length: int) -> list[float | None]:
    return [min(values[i + 1 - length : i + 1]) if i + 1 >= length else None for i in range(len(values))]


def pivot_high(values: list[float], left: int, right: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    for i in range(left, len(values) - right):
        window = values[i - left : i + right + 1]
        if values[i] == max(window):
            out[i + right] = values[i]
    return out


def pivot_low(values: list[float], left: int, right: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    for i in range(left, len(values) - right):
        window = values[i - left : i + right + 1]
        if values[i] == min(window):
            out[i + right] = values[i]
    return out


def crosses_over(prev_a: float, cur_a: float, prev_b: float, cur_b: float) -> bool:
    return prev_a <= prev_b and cur_a > cur_b


def crosses_under(prev_a: float, cur_a: float, prev_b: float, cur_b: float) -> bool:
    return prev_a >= prev_b and cur_a < cur_b


def after_entry_cutoff(ts: int) -> bool:
    dt = datetime.fromtimestamp(ts, tz=IST)
    return dt.hour * 60 + dt.minute >= 15 * 60


def should_flatten(ts: int) -> bool:
    dt = datetime.fromtimestamp(ts, tz=IST)
    return dt.hour * 60 + dt.minute >= 15 * 60 + 15


def fill_next_open(bars: list[Bar], i: int) -> tuple[int, float] | None:
    if i + 1 >= len(bars):
        return None
    nxt = bars[i + 1]
    return nxt.ts, nxt.open


def mrr_basic_signals(bars: list[Bar]) -> dict[str, list[Any]]:
    line = vwma(bars, 20)
    bull = [False] * len(bars)
    bear = [False] * len(bars)
    above = [False] * len(bars)
    for i, bar in enumerate(bars):
        if line[i] is not None:
            above[i] = bar.close >= line[i]
        if i == 0 or line[i] is None or line[i - 1] is None:
            continue
        bull[i] = crosses_over(bars[i - 1].close, bar.close, line[i - 1], line[i])
        bear[i] = crosses_under(bars[i - 1].close, bar.close, line[i - 1], line[i])
    return {"line": line, "bull": bull, "bear": bear, "above": above}


def combined_signals(bars: list[Bar]) -> dict[str, list[Any]]:
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]
    mrr = vwma(bars, 20)
    vwap = session_vwap(bars)
    ema_fast = ema(closes, 9)
    ema_slow = ema(closes, 21)
    rsi_val = rsi(closes, 14)
    vol_sma = sma(volumes, 20)
    ph = pivot_high(highs, 5, 5)
    pl = pivot_low(lows, 5, 5)
    hi_50 = highest(highs, 50)
    lo_50 = lowest(lows, 50)
    sig_sweep = [False] * len(bars)
    sig_breakout = [False] * len(bars)
    sig_fib = [False] * len(bars)
    sig_any = [False] * len(bars)
    exit_flip = [False] * len(bars)
    sup: float | None = None
    res: float | None = None
    for i, bar in enumerate(bars):
        if ph[i] is not None:
            res = ph[i]
        if pl[i] is not None:
            sup = pl[i]
        _ = res  # kept to mirror Pine state, even though current signals use only support.
        if mrr[i] is not None:
            bull_sweep = sup is not None and bar.low < sup and bar.close > sup
            sig_sweep[i] = bull_sweep and bar.close > mrr[i]
            sig_breakout[i] = (
                vwap[i] is not None
                and vol_sma[i] is not None
                and bar.close > mrr[i]
                and bar.close > vwap[i]
                and bar.volume > vol_sma[i] * 1.5
            )
        if (
            hi_50[i] is not None
            and lo_50[i] is not None
            and ema_fast[i] is not None
            and ema_slow[i] is not None
            and rsi_val[i] is not None
        ):
            fib_618 = hi_50[i] - ((hi_50[i] - lo_50[i]) * 0.618)
            sig_fib[i] = (
                bar.low <= fib_618
                and bar.close > ema_fast[i]
                and ema_fast[i] > ema_slow[i]
                and rsi_val[i] > 50
            )
        sig_any[i] = sig_sweep[i] or sig_breakout[i] or sig_fib[i]
        exit_flip[i] = mrr[i] is not None and bar.close < mrr[i]
    return {
        "mrr": mrr,
        "sweep": sig_sweep,
        "breakout": sig_breakout,
        "fib": sig_fib,
        "any": sig_any,
        "exit_flip": exit_flip,
    }


def trend_filters(bars: list[Bar]) -> dict[str, list[bool]]:
    """1m trend gate for the founder's MRR rerun.

    This is PROJECT-derived, not present in either Pine file:
    bullish trend = EMA9 > EMA21 > EMA50 and MRR rising for 5 bars.
    bearish trend = EMA9 < EMA21 < EMA50 and MRR falling for 5 bars.
    """
    closes = [b.close for b in bars]
    ema_fast = ema(closes, 9)
    ema_mid = ema(closes, 21)
    ema_slow = ema(closes, 50)
    mrr = vwma(bars, 20)
    bull = [False] * len(bars)
    bear = [False] * len(bars)
    for i, bar in enumerate(bars):
        if i < 5:
            continue
        if (
            ema_fast[i] is None
            or ema_mid[i] is None
            or ema_slow[i] is None
            or mrr[i] is None
            or mrr[i - 5] is None
        ):
            continue
        bull[i] = bar.close > ema_mid[i] and ema_fast[i] > ema_mid[i] > ema_slow[i] and mrr[i] > mrr[i - 5]
        bear[i] = bar.close < ema_mid[i] and ema_fast[i] < ema_mid[i] < ema_slow[i] and mrr[i] < mrr[i - 5]
    return {"bull": bull, "bear": bear}


def and_flags(left: list[bool], right: list[bool]) -> list[bool]:
    return [bool(a and b) for a, b in zip(left, right)]


def in_mrr_v2_window(ts: int) -> bool:
    dt = datetime.fromtimestamp(ts, tz=IST)
    minute = dt.hour * 60 + dt.minute
    return (9 * 60 + 20 <= minute <= 11 * 60) or (13 * 60 + 30 <= minute <= 15 * 60 + 10)


def mrr_v2_signals(bars: list[Bar]) -> list[bool]:
    """Founder-provided MRR Strategy V2 high-confluence long setup."""
    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]
    ema_fast = ema(closes, 9)
    ema_slow = ema(closes, 21)
    mrr = vwma(bars, 20)
    vol_ma = sma(volumes, 20)
    out = [False] * len(bars)
    for i, bar in enumerate(bars):
        if ema_fast[i] is None or ema_slow[i] is None or mrr[i] is None or vol_ma[i] is None:
            continue
        volume_confirmed = bar.volume > (vol_ma[i] * 1.3)
        trend_aligned = ema_fast[i] > ema_slow[i]
        mrr_retest = bar.low <= mrr[i] and bar.close > mrr[i]
        out[i] = mrr_retest and trend_aligned and volume_confirmed and in_mrr_v2_window(bar.ts)
    return out


def index_spot_alignment(bars: list[Bar]) -> dict[int, dict[str, bool]]:
    """Minute-bucket index alignment for option-chart entries.

    CALL premium entries require bullish spot alignment.
    PUT premium entries require bearish spot alignment.
    """
    closes = [b.close for b in bars]
    ema_fast = ema(closes, 9)
    ema_slow = ema(closes, 21)
    mrr = vwma(bars, 20)
    out: dict[int, dict[str, bool]] = {}
    for i, bar in enumerate(bars):
        if ema_fast[i] is None or ema_slow[i] is None or mrr[i] is None:
            continue
        out[bar.ts // 60] = {
            "CALL": bar.close > mrr[i] and ema_fast[i] > ema_slow[i],
            "PUT": bar.close < mrr[i] and ema_fast[i] < ema_slow[i],
        }
    return out


def dual_index_spot_bullish(bars: list[Bar]) -> dict[int, bool]:
    """Previous 1m spot bar equivalent of request.security(..., close[1]/vwap[1]/ema21[1])."""
    closes = [b.close for b in bars]
    spot_vwap = session_vwap(bars)
    spot_ema21 = ema(closes, 21)
    out: dict[int, bool] = {}
    for i, bar in enumerate(bars):
        if i == 0 or spot_vwap[i - 1] is None or spot_ema21[i - 1] is None:
            continue
        prev = bars[i - 1]
        out[bar.ts // 60] = prev.close > spot_vwap[i - 1] and prev.close > spot_ema21[i - 1]
    return out


def option_spot_gate(
    bars: list[Bar],
    option: str,
    spot_alignment: dict[int, dict[str, bool]] | None,
) -> list[bool]:
    if spot_alignment is None:
        return [False] * len(bars)
    return [bool(spot_alignment.get(bar.ts // 60, {}).get(option)) for bar in bars]


def dual_spot_gate(bars: list[Bar], spot_bullish: dict[int, bool] | None) -> list[bool]:
    if spot_bullish is None:
        return [False] * len(bars)
    return [bool(spot_bullish.get(bar.ts // 60)) for bar in bars]


def resample_5m_closes(bars: list[Bar]) -> tuple[list[int], list[float]]:
    buckets: dict[int, float] = {}
    order: list[int] = []
    for bar in bars:
        key = (bar.ts // 300) * 300
        if key not in buckets:
            order.append(key)
        buckets[key] = bar.close
    return order, [buckets[k] for k in order]


def mtf_5m_bullish_previous_bar(bars: list[Bar]) -> list[bool]:
    keys, closes = resample_5m_closes(bars)
    htf_ema = ema(closes, 21)
    state_by_key: dict[int, bool] = {}
    for i, key in enumerate(keys):
        if i == 0 or htf_ema[i - 1] is None:
            continue
        state_by_key[key] = closes[i - 1] > htf_ema[i - 1]
    return [bool(state_by_key.get((bar.ts // 300) * 300)) for bar in bars]


def master_option_scalper_signals(bars: list[Bar]) -> list[bool]:
    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]
    mrr = vwma(bars, 20)
    vwap = session_vwap(bars)
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    rsi_val = rsi(closes, 14)
    vol_ma = sma(volumes, 20)
    st_dir = supertrend_direction(bars, 10, 3.0)
    mtf_bullish = mtf_5m_bullish_previous_bar(bars)
    pl = pivot_low([b.low for b in bars], 5, 5)
    out = [False] * len(bars)
    sup_level: float | None = None
    for i, bar in enumerate(bars):
        if pl[i] is not None:
            sup_level = pl[i]
        required = (mrr[i], vwap[i], ema9[i], ema21[i], rsi_val[i], vol_ma[i], st_dir[i])
        if any(v is None for v in required):
            continue
        vol_confirmed = bar.volume > vol_ma[i] * 1.3  # type: ignore[operator]
        bull_sweep = sup_level is not None and bar.low < sup_level and bar.close > sup_level
        out[i] = (
            bar.close > mrr[i]  # type: ignore[operator]
            and bar.close > vwap[i]  # type: ignore[operator]
            and st_dir[i] == -1
            and ema9[i] > ema21[i]  # type: ignore[operator]
            and rsi_val[i] > 50  # type: ignore[operator]
            and mtf_bullish[i]
            and (vol_confirmed or bull_sweep)
            and in_mrr_v2_window(bar.ts)
        )
    return out


def dual_index_master_signals(bars: list[Bar], spot_bullish: list[bool]) -> list[bool]:
    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]
    mrr = vwma(bars, 20)
    vwap = session_vwap(bars)
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    vol_ma = sma(volumes, 20)
    st_dir = supertrend_direction(bars, 10, 3.0)
    out = [False] * len(bars)
    for i, bar in enumerate(bars):
        required = (mrr[i], vwap[i], ema9[i], ema21[i], vol_ma[i], st_dir[i])
        if any(v is None for v in required):
            continue
        out[i] = (
            bar.close > mrr[i]  # type: ignore[operator]
            and bar.close > vwap[i]  # type: ignore[operator]
            and st_dir[i] == -1
            and ema9[i] > ema21[i]  # type: ignore[operator]
            and spot_bullish[i]
            and bar.volume > vol_ma[i] * 1.3  # type: ignore[operator]
            and in_mrr_v2_window(bar.ts)
        )
    return out


def simulate_bracket_long(
    bars: list[Bar],
    entries: list[bool],
    *,
    strategy_id: str,
    chart_kind: str,
    underlying: str,
    series_key: str,
    side: str,
    stop_points: float = 12.0,
    target_points: float = 24.0,
) -> list[Trade]:
    """Next-bar entry with fixed point stop/target from signal close.

    Pine's same-bar stop/limit path is unknowable from OHLC if both are touched.
    This harness resolves that ambiguity conservatively by counting stop first.
    """
    trades: list[Trade] = []
    in_pos = False
    entry_ts = 0
    entry_px = 0.0
    stop_px = 0.0
    target_px = 0.0
    for i, bar in enumerate(bars):
        if in_pos:
            if should_flatten(bar.ts):
                trades.append(
                    Trade(strategy_id, chart_kind, underlying, series_key, side, entry_ts, bar.ts, entry_px, bar.close, bar.close - entry_px, "flatten_1515")
                )
                in_pos = False
                continue
            hit_stop = bar.low <= stop_px
            hit_target = bar.high >= target_px
            if hit_stop or hit_target:
                if hit_stop:
                    exit_px = stop_px
                    reason = "stop_12"
                else:
                    exit_px = target_px
                    reason = "target_24"
                trades.append(
                    Trade(strategy_id, chart_kind, underlying, series_key, side, entry_ts, bar.ts, entry_px, exit_px, exit_px - entry_px, reason)
                )
                in_pos = False
            continue
        if not entries[i] or after_entry_cutoff(bar.ts):
            continue
        fill = fill_next_open(bars, i)
        if fill is None:
            break
        entry_ts, entry_px = fill
        # The provided Pine template anchors stop/limit to the signal close.
        stop_px = bar.close - stop_points
        target_px = bar.close + target_points
        in_pos = True
    if in_pos and bars:
        last = bars[-1]
        trades.append(
            Trade(strategy_id, chart_kind, underlying, series_key, side, entry_ts, last.ts, entry_px, last.close, last.close - entry_px, "series_end")
        )
    return trades


def simulate_flip_index(
    bars: list[Bar],
    bull: list[bool],
    bear: list[bool],
    *,
    strategy_id: str,
    underlying: str,
    series_key: str,
) -> list[Trade]:
    trades: list[Trade] = []
    pos: str | None = None
    entry_ts = 0
    entry_px = 0.0
    for i, bar in enumerate(bars):
        if pos is not None and should_flatten(bar.ts):
            trades.append(
                Trade(strategy_id, "INDEX_PROXY", underlying, series_key, pos, entry_ts, bar.ts, entry_px, bar.close, _points(pos, entry_px, bar.close), "flatten_1515")
            )
            pos = None
            continue
        signal = "CE" if bull[i] else "PE" if bear[i] else None
        if signal is None or after_entry_cutoff(bar.ts):
            continue
        if pos == signal:
            continue
        fill = fill_next_open(bars, i)
        if fill is None:
            break
        if pos is not None:
            xts, xpx = fill
            trades.append(
                Trade(strategy_id, "INDEX_PROXY", underlying, series_key, pos, entry_ts, xts, entry_px, xpx, _points(pos, entry_px, xpx), "opposite_signal")
            )
        entry_ts, entry_px = fill
        pos = signal
    if pos is not None and bars:
        last = bars[-1]
        trades.append(
            Trade(strategy_id, "INDEX_PROXY", underlying, series_key, pos, entry_ts, last.ts, entry_px, last.close, _points(pos, entry_px, last.close), "series_end")
        )
    return trades


def simulate_long_entries(
    bars: list[Bar],
    entries: list[bool],
    exits: list[bool],
    *,
    strategy_id: str,
    chart_kind: str,
    underlying: str,
    series_key: str,
    side: str,
) -> list[Trade]:
    trades: list[Trade] = []
    in_pos = False
    entry_ts = 0
    entry_px = 0.0
    for i, bar in enumerate(bars):
        if in_pos and should_flatten(bar.ts):
            trades.append(
                Trade(strategy_id, chart_kind, underlying, series_key, side, entry_ts, bar.ts, entry_px, bar.close, bar.close - entry_px, "flatten_1515")
            )
            in_pos = False
            continue
        if in_pos:
            if exits[i]:
                fill = fill_next_open(bars, i)
                if fill is None:
                    break
                xts, xpx = fill
                trades.append(
                    Trade(strategy_id, chart_kind, underlying, series_key, side, entry_ts, xts, entry_px, xpx, xpx - entry_px, "mrr_state_flip")
                )
                in_pos = False
            continue
        if not entries[i] or after_entry_cutoff(bar.ts):
            continue
        fill = fill_next_open(bars, i)
        if fill is None:
            break
        entry_ts, entry_px = fill
        in_pos = True
    if in_pos and bars:
        last = bars[-1]
        trades.append(
            Trade(strategy_id, chart_kind, underlying, series_key, side, entry_ts, last.ts, entry_px, last.close, last.close - entry_px, "series_end")
        )
    return trades


def _points(side: str, entry: float, exit_: float) -> float:
    return exit_ - entry if side == "CE" else entry - exit_


def stats(trades: list[Trade]) -> dict[str, Any]:
    if not trades:
        return {
            "n": 0,
            "wins": 0,
            "win_rate": None,
            "expectancy_pts": None,
            "sum_pts": None,
            "profit_factor": None,
            "max_dd_pts": None,
            "first_entry_ist": None,
            "last_entry_ist": None,
        }
    pts = [t.points for t in trades]
    wins = sum(1 for p in pts if p > 0)
    gross_win = sum(p for p in pts if p > 0)
    gross_loss = abs(sum(p for p in pts if p < 0))
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pts:
        equity += p
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    return {
        "n": len(trades),
        "wins": wins,
        "win_rate": round(wins / len(trades), 4),
        "expectancy_pts": round(sum(pts) / len(trades), 4),
        "sum_pts": round(sum(pts), 4),
        "profit_factor": round(gross_win / gross_loss, 4) if gross_loss else None,
        "max_dd_pts": round(max_dd, 4),
        "first_entry_ist": ts_ist(trades[0].entry_ts),
        "last_entry_ist": ts_ist(trades[-1].entry_ts),
    }


def rated(trades: list[Trade], pnl_unit: str) -> dict[str, Any]:
    ordered = sorted(trades, key=lambda t: t.entry_ts)
    if not ordered:
        split = 0
    else:
        split = max(0, int(len(ordered) * 0.8))
    is_rows = ordered[:split]
    oos_rows = ordered[split:]
    return {
        "validated": False,
        "promote": False,
        "research_ready_for_programming": False,
        "pnl_unit": pnl_unit,
        "rating": "BACKTEST_REQUIRED" if len(oos_rows) < 30 else "SHADOW_METRIC_ONLY",
        "reason": "indicator-to-strategy assumptions need 06/09 review; option fills/costs/slippage not validated",
        "is": stats(is_rows),
        "oos": stats(oos_rows),
        "all": stats(ordered),
    }


def ts_ist(ts: int | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=IST).isoformat()


def load_index_series() -> dict[str, list[Bar]]:
    grouped: dict[str, list[Bar]] = {name: [] for name in INDEX_IDS.values()}
    for path in (ROOT / "data" / "recon" / "ohlc").glob("INDEX_IDX_I_*_1_*.json"):
        match = re.match(r"INDEX_IDX_I_(\d+)_1_", path.name)
        if not match or match.group(1) not in INDEX_IDS:
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        grouped[INDEX_IDS[match.group(1)]].extend(bars_from_chart(raw))
    return {k: dedupe_bars(v) for k, v in grouped.items() if v}


def load_premium_series() -> dict[tuple[str, str, str, str], list[Bar]]:
    grouped: dict[tuple[str, str, str, str], list[Bar]] = {}
    pattern = re.compile(
        r"(?P<segment>NSE_FNO|BSE_FNO)_(?P<sid>\d+)_(?P<expiry>WEEK|MONTH)_1_"
        r"(?P<strike>ATM(?:[+-]\d+)?)_(?P<option>CALL|PUT)_1_"
    )
    for path in (ROOT / "data" / "recon" / "ohlc" / "rolling").glob("*.json"):
        match = pattern.match(path.name)
        if not match or match.group("sid") not in INDEX_IDS:
            continue
        option = match.group("option")
        side = "ce" if option == "CALL" else "pe"
        raw = json.loads(path.read_text(encoding="utf-8"))
        bars = bars_from_rolling(raw, side)
        if not bars:
            continue
        key = (
            INDEX_IDS[match.group("sid")],
            match.group("expiry"),
            match.group("strike"),
            option,
        )
        grouped.setdefault(key, []).extend(bars)
    return {k: dedupe_bars(v) for k, v in grouped.items() if v}


def latest_state(bars: list[Bar]) -> dict[str, Any]:
    basic = mrr_basic_signals(bars)
    combined = combined_signals(bars)
    last_i = len(bars) - 1
    recent_basic = [
        {"ts_ist": ts_ist(bars[i].ts), "signal": "bull" if basic["bull"][i] else "bear"}
        for i in range(max(0, len(bars) - 100), len(bars))
        if basic["bull"][i] or basic["bear"][i]
    ][-5:]
    recent_combined = [
        {
            "ts_ist": ts_ist(bars[i].ts),
            "sweep": combined["sweep"][i],
            "breakout": combined["breakout"][i],
            "fib": combined["fib"][i],
        }
        for i in range(max(0, len(bars) - 100), len(bars))
        if combined["any"][i]
    ][-5:]
    return {
        "last_bar_ist": ts_ist(bars[last_i].ts) if bars else None,
        "last_close": bars[last_i].close if bars else None,
        "basic_above_mrr": basic["above"][last_i] if bars else None,
        "combined_exit_flip": combined["exit_flip"][last_i] if bars else None,
        "recent_basic_signals": recent_basic,
        "recent_combined_entries": recent_combined,
    }


def parse_paper_today() -> dict[str, Any]:
    latest_path = OUT_DIR / "paper_latest_signals.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8")) if latest_path.exists() else {}
    day = latest.get("day") or datetime.now(IST).date().isoformat()
    watch_dir = OUT_DIR / "paper_watch"
    watch_summary: dict[str, Any] = {}
    for path in sorted(watch_dir.glob(f"*/{day}.jsonl")):
        rows = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        if not rows:
            continue
        last = rows[-1]
        tickets = last.get("tickets") or []
        lean_counts: dict[str, int] = {}
        for ticket in tickets:
            lean = str(ticket.get("lean") or ticket.get("final_lean") or "UNKNOWN")
            lean_counts[lean] = lean_counts.get(lean, 0) + 1
        watch_summary[path.parent.name] = {
            "rows": len(rows),
            "last_as_of_ist": last.get("as_of_ist") or (last.get("clock") or {}).get("as_of_ist"),
            "lean_counts_last_row": lean_counts,
            "has_ohlc_arrays": has_ohlc_arrays(last),
        }
    return {
        "paper_latest_signals": latest,
        "watch_summary": watch_summary,
        "current_mrr_status": "DATA_INSUFFICIENT: today's paper-watch/probe files do not persist OHLC arrays needed to reproduce Pine indicators",
    }


def has_ohlc_arrays(obj: Any) -> bool:
    if isinstance(obj, dict):
        keys = set(obj)
        if {"open", "high", "low", "close", "timestamp"}.issubset(keys):
            return True
        return any(has_ohlc_arrays(v) for v in obj.values())
    if isinstance(obj, list):
        return any(has_ohlc_arrays(v) for v in obj[:5])
    return False


def run() -> dict[str, Any]:
    index_series = load_index_series()
    premium_series = load_premium_series()
    spot_alignment_by_underlying = {
        underlying: index_spot_alignment(bars) for underlying, bars in index_series.items()
    }
    dual_spot_bullish_by_underlying = {
        underlying: dual_index_spot_bullish(bars)
        for underlying, bars in index_series.items()
        if underlying in {"NIFTY", "SENSEX"}
    }
    index_results: dict[str, Any] = {}
    premium_results: dict[str, Any] = {}

    for underlying, bars in index_series.items():
        basic = mrr_basic_signals(bars)
        combined = combined_signals(bars)
        trends = trend_filters(bars)
        v2 = mrr_v2_signals(bars)
        t_basic = simulate_flip_index(
            bars,
            basic["bull"],
            basic["bear"],
            strategy_id="MRR-PINE-1-INDEX-PROXY",
            underlying=underlying,
            series_key=f"{underlying}/INDEX/1m",
        )
        t_combined = simulate_long_entries(
            bars,
            combined["any"],
            combined["exit_flip"],
            strategy_id="MRR-COMBINED-INDEX-CE-PROXY",
            chart_kind="INDEX_PROXY",
            underlying=underlying,
            series_key=f"{underlying}/INDEX/1m",
            side="CE",
        )
        t_basic_trend = simulate_flip_index(
            bars,
            and_flags(basic["bull"], trends["bull"]),
            and_flags(basic["bear"], trends["bear"]),
            strategy_id="MRR-PINE-1-TREND-INDEX-PROXY",
            underlying=underlying,
            series_key=f"{underlying}/INDEX/1m/TREND",
        )
        t_combined_trend = simulate_long_entries(
            bars,
            and_flags(combined["any"], trends["bull"]),
            combined["exit_flip"],
            strategy_id="MRR-COMBINED-TREND-INDEX-CE-PROXY",
            chart_kind="INDEX_PROXY",
            underlying=underlying,
            series_key=f"{underlying}/INDEX/1m/TREND",
            side="CE",
        )
        t_v2 = simulate_bracket_long(
            bars,
            v2,
            strategy_id="MRR-V2-HIGH-CONFLUENCE-INDEX-CE-PROXY",
            chart_kind="INDEX_PROXY",
            underlying=underlying,
            series_key=f"{underlying}/INDEX/1m/MRR_V2",
            side="CE",
        )
        index_results[underlying] = {
            "bars": len(bars),
            "first_bar_ist": ts_ist(bars[0].ts),
            "last_bar_ist": ts_ist(bars[-1].ts),
            "mrr_pine_1": rated(t_basic, "UNDERLYING_POINTS_PROXY"),
            "mrr_combined": rated(t_combined, "UNDERLYING_POINTS_PROXY"),
            "mrr_pine_1_trend": rated(t_basic_trend, "UNDERLYING_POINTS_PROXY"),
            "mrr_combined_trend": rated(t_combined_trend, "UNDERLYING_POINTS_PROXY"),
            "mrr_v2_high_confluence": rated(t_v2, "UNDERLYING_POINTS_PROXY"),
            "latest_cached_state": latest_state(bars),
        }

    for key, bars in premium_series.items():
        underlying, expiry, strike, option = key
        series_key = f"{underlying}/{expiry}/{strike}/{option}/1m"
        basic = mrr_basic_signals(bars)
        combined = combined_signals(bars)
        trends = trend_filters(bars)
        v2 = mrr_v2_signals(bars)
        master = master_option_scalper_signals(bars)
        spot_gate = option_spot_gate(bars, option, spot_alignment_by_underlying.get(underlying))
        dual_gate = dual_spot_gate(bars, dual_spot_bullish_by_underlying.get(underlying))
        dual_master = (
            dual_index_master_signals(bars, dual_gate)
            if option == "CALL" and underlying in {"NIFTY", "SENSEX"}
            else [False] * len(bars)
        )
        t_basic = simulate_long_entries(
            bars,
            basic["bull"],
            basic["bear"],
            strategy_id="MRR-PINE-1-PREMIUM-LONG",
            chart_kind="OPTION_PREMIUM",
            underlying=underlying,
            series_key=series_key,
            side=f"{option}_LONG",
        )
        t_combined = simulate_long_entries(
            bars,
            combined["any"],
            combined["exit_flip"],
            strategy_id="MRR-COMBINED-PREMIUM-LONG",
            chart_kind="OPTION_PREMIUM",
            underlying=underlying,
            series_key=series_key,
            side=f"{option}_LONG",
        )
        t_basic_trend = simulate_long_entries(
            bars,
            and_flags(basic["bull"], trends["bull"]),
            basic["bear"],
            strategy_id="MRR-PINE-1-TREND-PREMIUM-LONG",
            chart_kind="OPTION_PREMIUM",
            underlying=underlying,
            series_key=f"{series_key}/TREND",
            side=f"{option}_LONG",
        )
        t_combined_trend = simulate_long_entries(
            bars,
            and_flags(combined["any"], trends["bull"]),
            combined["exit_flip"],
            strategy_id="MRR-COMBINED-TREND-PREMIUM-LONG",
            chart_kind="OPTION_PREMIUM",
            underlying=underlying,
            series_key=f"{series_key}/TREND",
            side=f"{option}_LONG",
        )
        t_v2 = simulate_bracket_long(
            bars,
            v2,
            strategy_id="MRR-V2-HIGH-CONFLUENCE-PREMIUM-LONG",
            chart_kind="OPTION_PREMIUM",
            underlying=underlying,
            series_key=f"{series_key}/MRR_V2",
            side=f"{option}_LONG",
        )
        t_v2_spot = simulate_bracket_long(
            bars,
            and_flags(v2, spot_gate),
            strategy_id="MRR-V2-HIGH-CONFLUENCE-SPOT-ALIGNED-PREMIUM-LONG",
            chart_kind="OPTION_PREMIUM",
            underlying=underlying,
            series_key=f"{series_key}/MRR_V2_SPOT_ALIGNED",
            side=f"{option}_LONG",
        )
        t_master = []
        t_master_spot = []
        if option == "CALL":
            t_master = simulate_bracket_long(
                bars,
                master,
                strategy_id="MASTER-OPTION-SCALPER-CALL",
                chart_kind="OPTION_PREMIUM",
                underlying=underlying,
                series_key=f"{series_key}/MASTER",
                side="CALL_LONG",
                target_points=25.0,
            )
            t_master_spot = simulate_bracket_long(
                bars,
                and_flags(master, spot_gate),
                strategy_id="MASTER-OPTION-SCALPER-CALL-SPOT-ALIGNED",
                chart_kind="OPTION_PREMIUM",
                underlying=underlying,
                series_key=f"{series_key}/MASTER_SPOT_ALIGNED",
                side="CALL_LONG",
                target_points=25.0,
            )
        t_dual_master = []
        if option == "CALL" and underlying in {"NIFTY", "SENSEX"}:
            t_dual_master = simulate_bracket_long(
                bars,
                dual_master,
                strategy_id="DUAL-INDEX-MASTER-OPTION-ENGINE-CALL",
                chart_kind="OPTION_PREMIUM",
                underlying=underlying,
                series_key=f"{series_key}/DUAL_INDEX_MASTER",
                side="CALL_LONG",
                stop_points=15.0 if underlying == "SENSEX" else 10.0,
                target_points=30.0 if underlying == "SENSEX" else 20.0,
            )
        premium_results[series_key] = {
            "bars": len(bars),
            "first_bar_ist": ts_ist(bars[0].ts),
            "last_bar_ist": ts_ist(bars[-1].ts),
            "mrr_pine_1": rated(t_basic, "OPTION_PREMIUM_POINTS_GROSS"),
            "mrr_combined": rated(t_combined, "OPTION_PREMIUM_POINTS_GROSS"),
            "mrr_pine_1_trend": rated(t_basic_trend, "OPTION_PREMIUM_POINTS_GROSS"),
            "mrr_combined_trend": rated(t_combined_trend, "OPTION_PREMIUM_POINTS_GROSS"),
            "mrr_v2_high_confluence": rated(t_v2, "OPTION_PREMIUM_POINTS_GROSS"),
            "mrr_v2_spot_aligned": rated(t_v2_spot, "OPTION_PREMIUM_POINTS_GROSS"),
            "latest_cached_state": latest_state(bars),
        }
        if option == "CALL":
            premium_results[series_key]["master_option_scalper"] = rated(t_master, "OPTION_PREMIUM_POINTS_GROSS")
            premium_results[series_key]["master_option_scalper_spot_aligned"] = rated(
                t_master_spot, "OPTION_PREMIUM_POINTS_GROSS"
            )
        if option == "CALL" and underlying in {"NIFTY", "SENSEX"}:
            premium_results[series_key]["dual_index_master"] = rated(
                t_dual_master, "OPTION_PREMIUM_POINTS_GROSS"
            )

    return {
        "kind": "MRR_PINE_SHADOW_BACKTEST",
        "as_of_ist": datetime.now(IST).isoformat(timespec="seconds"),
        "source_files": [
            "teams/04_quant/docs/mrr/mrr_indcator_pine_script_1.txt",
            "teams/04_quant/docs/mrr/mrr_indicator_pine_sript_combine.txt",
        ],
        "scope": {
            "historical_cache": "cached 1m index and rolling option-premium OHLC under data/recon/ohlc",
            "current_cache": "today's paper loop files under data/recon/paper_*; no live order use",
        },
        "assumptions": [
            "Pine files are indicators, not strategies; this harness defines entries/exits for measurement only.",
            "Only regular-session chart bars are used: 09:15-15:30 IST.",
            "Trend-gated variants are PROJECT-derived: EMA9/EMA21/EMA50 alignment plus 5-bar MRR slope on 1m candles.",
            "Fills use next bar open after the signal close to reduce look-ahead bias.",
            "MRR Pine 1 index proxy: bullish crossover = CE proxy, bearish crossunder = PE proxy; exit/reverse on opposite signal.",
            "MRR Pine 1 premium chart: bullish crossover buys that option premium; bearish crossunder exits.",
            "Combined script: any SWEEP/BREAKOUT/FIB marker enters long; close below MRR exits; no target/SL was present in Pine.",
            "MRR V2 high-confluence: MRR retest + EMA9>EMA21 + volume > SMA20*1.3 + 09:20-11:00/13:30-15:10 windows; 12-point stop and 24-point target anchored to signal close.",
            "MRR V2 spot-aligned premium variant: CALL premium entries require index close > index MRR and EMA9>EMA21; PUT premium entries require index close < index MRR and EMA9<EMA21 on the same 1m bucket.",
            "Master Option Scalper is tested on CALL premium charts only: close > MRR/VWAP, SuperTrend bullish, EMA9>EMA21, RSI>50, previous completed 5m close > 5m EMA21, volume spike or bull sweep, and the same time windows.",
            "Dual-Index Master is tested on NIFTY and SENSEX CALL premium charts only: option close > MRR/VWAP, SuperTrend bullish, EMA9>EMA21, volume spike, time window, and previous 1m spot close > spot VWAP and EMA21.",
            "Dual-Index Master risk uses NIFTY 10/20 points and SENSEX 15/30 points exactly as requested.",
            "MRR V2 bracket ambiguity is conservative: if a bar touches both stop and target, stop is counted first.",
            "Positions flatten after 15:15 IST; no new entries after 15:00 IST.",
            "Premium results are gross premium points before brokerage, spread, slippage, fills, taxes, lot sizing, and liquidity filters.",
        ],
        "policy": {
            "validated": False,
            "promote": False,
            "orders": "REFUSED",
            "win_rate_language": "Measured backtest/shadow metric only, not a customer claim.",
        },
        "data_coverage": {
            "index_series": len(index_results),
            "premium_series": len(premium_results),
            "index_bars_total": sum(v["bars"] for v in index_results.values()),
            "premium_bars_total": sum(v["bars"] for v in premium_results.values()),
        },
        "historical": {
            "index": index_results,
            "premium": premium_results,
        },
        "current": parse_paper_today(),
    }


def compact_table(result: dict[str, Any]) -> str:
    lines = [
        "# MRR Pine Shadow Backtest",
        "",
        f"Generated: `{result['as_of_ist']}`",
        "",
        "This is a measured shadow backtest only. `validated=false`, `promote=false`, and orders stay refused.",
        "",
        "## Assumptions",
    ]
    lines.extend(f"- {item}" for item in result["assumptions"])
    lines.extend(["", "## Historical Index Proxy"])
    lines.append("| Underlying | Bars | Script | Trades | Win Rate | OOS Win Rate | Expectancy Pts | OOS Expectancy |")
    lines.append("|---|---:|---|---:|---:|---:|---:|---:|")
    for underlying, row in result["historical"]["index"].items():
        for label in (
            "mrr_pine_1",
            "mrr_pine_1_trend",
            "mrr_combined",
            "mrr_combined_trend",
            "mrr_v2_high_confluence",
        ):
            all_s = row[label]["all"]
            oos_s = row[label]["oos"]
            lines.append(
                f"| {underlying} | {row['bars']} | {label} | {all_s['n']} | {fmt(all_s['win_rate'])} | {fmt(oos_s['win_rate'])} | {fmt(all_s['expectancy_pts'])} | {fmt(oos_s['expectancy_pts'])} |"
            )
    lines.extend(["", "## Historical Option Premium Summary"])
    lines.append("| Underlying | Script | Series | Trades | Win Rate | OOS Win Rate | Expectancy Pts | OOS Expectancy |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for series_key, row in result["historical"]["premium"].items():
        underlying = series_key.split("/", 1)[0]
        for label in (
            "mrr_pine_1",
            "mrr_pine_1_trend",
            "mrr_combined",
            "mrr_combined_trend",
            "mrr_v2_high_confluence",
            "mrr_v2_spot_aligned",
            "master_option_scalper",
            "master_option_scalper_spot_aligned",
            "dual_index_master",
        ):
            if label in row:
                grouped.setdefault((underlying, label), []).append(row[label])
    for (underlying, label), rows in sorted(grouped.items()):
        trades = sum(r["all"]["n"] for r in rows)
        wins = sum(r["all"]["wins"] for r in rows)
        oos_trades = sum(r["oos"]["n"] for r in rows)
        oos_wins = sum(r["oos"]["wins"] for r in rows)
        total_pts = sum((r["all"]["sum_pts"] or 0.0) for r in rows)
        oos_pts = sum((r["oos"]["sum_pts"] or 0.0) for r in rows)
        lines.append(
            f"| {underlying} | {label} | {len(rows)} | {trades} | {fmt(wins / trades if trades else None)} | {fmt(oos_wins / oos_trades if oos_trades else None)} | {fmt(total_pts / trades if trades else None)} | {fmt(oos_pts / oos_trades if oos_trades else None)} |"
        )
    lines.extend(["", "## Current Loop"])
    current = result["current"]
    latest = current.get("paper_latest_signals") or {}
    lines.append(f"- Latest paper signal file day: `{latest.get('day')}` updated `{latest.get('updated_at_ist')}`.")
    lines.append(f"- Lean counts: `{json.dumps(latest.get('lean_counts') or {}, sort_keys=True)}`.")
    lines.append(f"- MRR current-chart status: `{current.get('current_mrr_status')}`.")
    lines.append("")
    lines.append("## Required Next Step")
    lines.append("- Persist current OHLC arrays from the running loop if you want true intraday MRR replay for today. Current paper-watch files store decisions/reasons, not enough candle data to recompute Pine.")
    return "\n".join(lines) + "\n"


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:.4f}"
    return str(value)


def main() -> None:
    result = run()
    day = (result["current"].get("paper_latest_signals") or {}).get("day") or datetime.now(IST).date().isoformat()
    json_path = OUT_DIR / f"MRR_BACKTEST_{day}.json"
    md_path = OUT_DIR / f"MRR_BACKTEST_{day}.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    md_path.write_text(compact_table(result), encoding="utf-8")
    print(json_path.relative_to(ROOT))
    print(md_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
