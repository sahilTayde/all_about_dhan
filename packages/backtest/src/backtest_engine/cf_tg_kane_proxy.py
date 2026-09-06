"""Chart Fanatics Phase-6 OHLC proxies — TG Capital + Trader Kane.

EXTERNAL guests — not DHAN-DERIVED. Structure proxies only.
ASR transcripts — not YouTube captions. No win-rate claim. No live orders.
Title '90%' (TG) = marketing, not product metric.
"""

from __future__ import annotations

from typing import Optional

from backtest_engine.indicators import Bar, ema


def _is_swing_high(bars: list[Bar], i: int) -> bool:
    if i < 1 or i >= len(bars) - 1:
        return False
    return bars[i].high >= bars[i - 1].high and bars[i].high >= bars[i + 1].high


def _is_swing_low(bars: list[Bar], i: int) -> bool:
    if i < 1 or i >= len(bars) - 1:
        return False
    return bars[i].low <= bars[i - 1].low and bars[i].low <= bars[i + 1].low


def _is_doji(bar: Bar, *, max_body_frac: float = 0.35) -> bool:
    rng = bar.high - bar.low
    if rng <= 0:
        return False
    body = abs(bar.close - bar.open)
    return body / rng <= max_body_frac


def lean_cf_tg_trident(
    bars: list[Bar],
    *,
    max_body_frac: float = 0.35,
    fvg_lookback: int = 6,
) -> list[str]:
    """FVG + doji into mid-gap + confirm close (trident stand-in).

    Find a recent 3-bar FVG; require prior bar to be doji that tags gap CE (50%);
    confirm bar closes back through doji extreme (long: close < doji high).
    London killzone / 30m clock not modeled — 3m structure only.
    """
    n = len(bars)
    out = ["SKIP"] * n
    for i in range(4, n):
        doji = bars[i - 1]
        if not _is_doji(doji, max_body_frac=max_body_frac):
            continue
        # Search recent FVG ending before the doji
        start = max(2, i - 1 - fvg_lookback)
        for gap_end in range(i - 2, start - 1, -1):
            a = bars[gap_end - 2]
            c = bars[gap_end]
            # Bullish FVG (displacement up)
            if a.high < c.low:
                mid = 0.5 * (a.high + c.low)
                if doji.low <= mid <= doji.high and bars[i].close < doji.high:
                    out[i] = "CE"
                    break
            # Bearish FVG
            if a.low > c.high and out[i] == "SKIP":
                mid = 0.5 * (a.low + c.high)
                if doji.low <= mid <= doji.high and bars[i].close > doji.low:
                    out[i] = "PE"
                    break
    return out


def lean_cf_tg_ema_wave(
    bars: list[Bar],
    *,
    mid_len: int = 13,
    pullback_bars: int = 3,
) -> list[str]:
    """EMA stack 5>9>mid>21 + above EMA200 (or inverse) after shallow pullback.

    ASR mid EMA is 13 or 15 — default 13; ablation may flip.
    London session not modeled.
    """
    n = len(bars)
    out = ["SKIP"] * n
    closes = [b.close for b in bars]
    e5 = ema(closes, 5)
    e9 = ema(closes, 9)
    em = ema(closes, mid_len)
    e21 = ema(closes, 21)
    e200 = ema(closes, 200)

    for i in range(200, n):
        vals = (e5[i], e9[i], em[i], e21[i], e200[i])
        if any(v is None for v in vals):
            continue
        v5, v9, vm, v21, v200 = vals  # type: ignore[misc]
        stacked_up = v5 > v9 > vm > v21 and closes[i] > v200
        stacked_dn = v5 < v9 < vm < v21 and closes[i] < v200
        if not (stacked_up or stacked_dn):
            continue
        # Shallow pullback: within last pullback_bars, low tagged near e9 then close resumes
        window = bars[max(0, i - pullback_bars) : i + 1]
        if stacked_up:
            tagged = any(b.low <= v9 * 1.001 for b in window[:-1]) if len(window) > 1 else False
            if tagged and closes[i] > v9 and (i == 0 or closes[i - 1] <= closes[i]):
                out[i] = "CE"
        elif stacked_dn:
            tagged = any(b.high >= v9 * 0.999 for b in window[:-1]) if len(window) > 1 else False
            if tagged and closes[i] < v9 and (i == 0 or closes[i - 1] >= closes[i]):
                out[i] = "PE"
    return out


def lean_cf_kane_eq50(
    bars: list[Bar],
    *,
    lookback: int = 40,
    touch_frac: float = 0.002,
) -> list[str]:
    """50% equilibrium base-hit proxy.

    After confirmed swing high/low range, price tags mid then leans with
    the impulse that built the range (continuation base-hit).
    Nested EQ / SMT not modeled.
    """
    n = len(bars)
    out = ["SKIP"] * n
    for i in range(5, n):
        start = max(1, i - lookback)
        # Find most recent swing high and swing low before i
        hi_i: Optional[int] = None
        lo_i: Optional[int] = None
        for j in range(i - 2, start - 1, -1):
            if hi_i is None and _is_swing_high(bars, j):
                hi_i = j
            if lo_i is None and _is_swing_low(bars, j):
                lo_i = j
            if hi_i is not None and lo_i is not None:
                break
        if hi_i is None or lo_i is None:
            continue
        hi = bars[hi_i].high
        lo = bars[lo_i].low
        if hi <= lo:
            continue
        mid = 0.5 * (hi + lo)
        bar = bars[i]
        if abs(bar.low - mid) / mid <= touch_frac or abs(bar.high - mid) / mid <= touch_frac:
            # Impulse direction: whichever swing is more recent defines late extreme;
            # lean continuation away from mid toward the later extreme's side.
            if hi_i > lo_i:
                # Last extreme was high → prior move up; base-hit long from mid
                if bar.close > mid:
                    out[i] = "CE"
            else:
                if bar.close < mid:
                    out[i] = "PE"
    return out


def lean_cf_kane_po3_sweep(
    bars: list[Bar],
    *,
    lookback: int = 20,
    confirm_bars: int = 4,
) -> list[str]:
    """PO3 manipulation stand-in: sweep swing extreme then close back.

    PE = sweep swing high then close back below it.
    CE = sweep swing low then close back above it.
    True multi-TF PO3 boxes + NQ/ES SMT = DATA_INSUFFICIENT — not modeled.
    """
    _ = lookback
    n = len(bars)
    out = ["SKIP"] * n
    hi_level: Optional[float] = None
    lo_level: Optional[float] = None
    hi_sweep_i: Optional[int] = None
    lo_sweep_i: Optional[int] = None
    done_hi = False
    done_lo = False

    for i in range(2, n):
        j = i - 2
        if j >= 1:
            if _is_swing_high(bars, j):
                hi_level = bars[j].high
                hi_sweep_i = None
                done_hi = False
            if _is_swing_low(bars, j):
                lo_level = bars[j].low
                lo_sweep_i = None
                done_lo = False

        if hi_level is not None and not done_hi:
            if hi_sweep_i is None and bars[i].high > hi_level:
                hi_sweep_i = i
            elif hi_sweep_i is not None and 0 < i - hi_sweep_i <= confirm_bars:
                if bars[i].close < hi_level:
                    out[i] = "PE"
                    done_hi = True

        if lo_level is not None and not done_lo:
            if lo_sweep_i is None and bars[i].low < lo_level:
                lo_sweep_i = i
            elif lo_sweep_i is not None and 0 < i - lo_sweep_i <= confirm_bars:
                if bars[i].close > lo_level:
                    if out[i] == "SKIP":
                        out[i] = "CE"
                    done_lo = True

        if hi_sweep_i is not None and i - hi_sweep_i > confirm_bars:
            hi_sweep_i = None
        if lo_sweep_i is not None and i - lo_sweep_i > confirm_bars:
            lo_sweep_i = None

    return out


def gap_summary_tg_kane() -> dict[str, str]:
    return {
        "transcript_source": "ASR_WHISPER_NOT_YT_CAPTIONS",
        "gex_option_chain": "NOT_IN_RECIPE",
        "order_flow": "NOT_REQUIRED_BY_GUESTS",
        "london_kz_ny_to_nse": "DATA_INSUFFICIENT",
        "est_0915_1100_to_nse": "DATA_INSUFFICIENT",
        "tg_title_90pct_wr": "MARKETING_NOT_PRODUCT_METRIC",
        "tg_ema_13_vs_15": "ASR_UNKNOWN_DEFAULT_13",
        "kane_smt_nq_es": "DATA_INSUFFICIENT_SINGLE_INDEX",
        "kane_multi_tf_po3_boxes": "NOT_FROZEN",
        "proxy_layer": "PROJECT_MIX_OHLC",
        "teacher_assets": "FX_GOLD_NQ_ES_CRYPTO",
    }
