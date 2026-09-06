"""Chart Fanatics Phase-4 OHLC proxies — Marco + Trader Mayne.

EXTERNAL guests — not DHAN-DERIVED. Structure proxies only.
ASR transcripts — not YouTube captions. No win-rate claim. No live orders.
"""

from __future__ import annotations

from typing import Optional

from backtest_engine.indicators import Bar


def _is_swing_high(bars: list[Bar], i: int) -> bool:
    if i < 1 or i >= len(bars) - 1:
        return False
    return bars[i].high >= bars[i - 1].high and bars[i].high >= bars[i + 1].high


def _is_swing_low(bars: list[Bar], i: int) -> bool:
    if i < 1 or i >= len(bars) - 1:
        return False
    return bars[i].low <= bars[i - 1].low and bars[i].low <= bars[i + 1].low


def lean_cf_marco_sweep_reclaim(
    bars: list[Bar],
    *,
    lookback: int = 20,  # reserved / ablation grid
    confirm_bars: int = 4,
) -> list[str]:
    """Sweep recent swing extreme then close back through (liquidity trap proxy).

    PE = sweep swing high then close back below it.
    CE = sweep swing low then close back above it.
    No retail OB/induce narrative — structure only.
    """
    _ = lookback
    n = len(bars)
    out = ["SKIP"] * n
    hi_sweep_i: Optional[int] = None
    hi_level: Optional[float] = None
    lo_sweep_i: Optional[int] = None
    lo_level: Optional[float] = None
    done_hi = False
    done_lo = False

    for i in range(2, n):
        # Confirm swings with one-bar lag (need right neighbor settled) so reclaim
        # on bar i is not wiped by treating i-1 as a fresh swing high/low.
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

        # Expire stale sweeps
        if hi_sweep_i is not None and i - hi_sweep_i > confirm_bars:
            hi_sweep_i = None
        if lo_sweep_i is not None and i - lo_sweep_i > confirm_bars:
            lo_sweep_i = None

    return out


def lean_cf_marco_eq_sweep(
    bars: list[Bar],
    *,
    lookback: int = 40,
    equal_frac: float = 0.0008,
    confirm_bars: int = 4,
) -> list[str]:
    """Near-equal highs/lows then sweep + reclaim (INT-EXT / equal-pool proxy).

    equal_frac is PROJECT HYPOTHESIS (not spoken) — fraction of price.
    """
    n = len(bars)
    out = ["SKIP"] * n
    for i in range(5, n):
        start = max(0, i - lookback)
        swing_highs: list[float] = []
        swing_lows: list[float] = []
        for j in range(start + 1, i - 1):
            if _is_swing_high(bars, j):
                swing_highs.append(bars[j].high)
            if _is_swing_low(bars, j):
                swing_lows.append(bars[j].low)

        eq_hi: Optional[float] = None
        for a in range(len(swing_highs)):
            for b_idx in range(a + 1, len(swing_highs)):
                mid = 0.5 * (swing_highs[a] + swing_highs[b_idx])
                if mid > 0 and abs(swing_highs[a] - swing_highs[b_idx]) / mid <= equal_frac:
                    eq_hi = max(swing_highs[a], swing_highs[b_idx])
                    break
            if eq_hi is not None:
                break

        eq_lo: Optional[float] = None
        for a in range(len(swing_lows)):
            for b_idx in range(a + 1, len(swing_lows)):
                mid = 0.5 * (swing_lows[a] + swing_lows[b_idx])
                if mid > 0 and abs(swing_lows[a] - swing_lows[b_idx]) / mid <= equal_frac:
                    eq_lo = min(swing_lows[a], swing_lows[b_idx])
                    break
            if eq_lo is not None:
                break

        # One-shot: if this bar sweeps, look ahead within confirm for reclaim
        if eq_hi is not None and bars[i].high > eq_hi:
            for k in range(i + 1, min(n, i + confirm_bars + 1)):
                if bars[k].close < eq_hi and out[k] == "SKIP":
                    out[k] = "PE"
                    break
        if eq_lo is not None and bars[i].low < eq_lo:
            for k in range(i + 1, min(n, i + confirm_bars + 1)):
                if bars[k].close > eq_lo and out[k] == "SKIP":
                    out[k] = "CE"
                    break
    return out


def lean_cf_mayne_msb_discount(
    bars: list[Bar],
    *,
    pullback_bars: int = 40,
) -> list[str]:
    """Close beyond 3-candle swing (MSB) then lean on pullback into discount/premium half.

    Long: after bullish MSB, wait pullback into lower half of post-MSB range → CE.
    Short: after bearish MSB, wait pullback into upper half → PE.
    OB candle-combine not modeled — half-range stand-in.
    """
    n = len(bars)
    out = ["SKIP"] * n
    state: Optional[dict] = None

    for i in range(3, n):
        # Swing confirmed at i-2 (neighbors i-3 and i-1 already known)
        mid = i - 2
        if mid < 1:
            continue
        is_sh = _is_swing_high(bars, mid)
        is_sl = _is_swing_low(bars, mid)

        if is_sh and bars[i].close > bars[mid].high:
            sl_px = min(b.low for b in bars[max(0, mid - 20) : mid + 1])
            state = {"side": "CE", "lo": sl_px, "hi": bars[mid].high, "i0": i}
        elif is_sl and bars[i].close < bars[mid].low:
            sh_px = max(b.high for b in bars[max(0, mid - 20) : mid + 1])
            state = {"side": "PE", "lo": bars[mid].low, "hi": sh_px, "i0": i}

        if state is None:
            continue
        if i - state["i0"] > pullback_bars:
            state = None
            continue
        if i <= state["i0"]:
            continue

        mid_px = 0.5 * (state["lo"] + state["hi"])
        bar = bars[i]
        if state["side"] == "CE" and bar.low <= mid_px and bar.close >= mid_px:
            out[i] = "CE"
            state = None
        elif state["side"] == "PE" and bar.high >= mid_px and bar.close <= mid_px:
            out[i] = "PE"
            state = None

    return out


def lean_cf_mayne_breaker(
    bars: list[Bar],
    *,
    lookback: int = 20,
    max_gap: int = 12,
) -> list[str]:
    """Sweep recent swing then close beyond opposite swing (breaker proxy).

    Long: take swing low, then close above a prior swing high within lookback.
    Short: take swing high, then close below a prior swing low.
    No HTF OB gate — honesty gap.
    """
    n = len(bars)
    out = ["SKIP"] * n
    # Track pending sweeps
    pending_long: Optional[tuple[float, float, int]] = None  # (swept_low, break_high, sweep_i)
    pending_short: Optional[tuple[float, float, int]] = None

    for i in range(3, n):
        j = i - 1
        # Find prior swings
        prior_sh: Optional[float] = None
        prior_sl: Optional[float] = None
        for k in range(j - 1, max(1, j - lookback) - 1, -1):
            if prior_sh is None and _is_swing_high(bars, k):
                prior_sh = bars[k].high
            if prior_sl is None and _is_swing_low(bars, k):
                prior_sl = bars[k].low
            if prior_sh is not None and prior_sl is not None:
                break

        if _is_swing_low(bars, j) and prior_sh is not None:
            pending_long = (bars[j].low, prior_sh, -1)

        if _is_swing_high(bars, j) and prior_sl is not None:
            pending_short = (bars[j].high, prior_sl, -1)

        if pending_long is not None:
            level_lo, level_hi, sweep_i = pending_long
            if sweep_i < 0 and bars[i].low < level_lo:
                pending_long = (level_lo, level_hi, i)
            elif sweep_i >= 0:
                if i - sweep_i > max_gap:
                    pending_long = None
                elif bars[i].close > level_hi:
                    out[i] = "CE"
                    pending_long = None

        if pending_short is not None:
            level_hi, level_lo, sweep_i = pending_short
            if sweep_i < 0 and bars[i].high > level_hi:
                pending_short = (level_hi, level_lo, i)
            elif sweep_i >= 0:
                if i - sweep_i > max_gap:
                    pending_short = None
                elif bars[i].close < level_lo:
                    if out[i] == "SKIP":
                        out[i] = "PE"
                    pending_short = None

    return out


def gap_summary_marco_mayne() -> dict[str, str]:
    return {
        "transcript_source": "ASR_WHISPER_NOT_YT_CAPTIONS",
        "gex_option_chain": "NOT_IN_RECIPE",
        "order_flow": "NOT_REQUIRED_BY_GUESTS",
        "ny_asia_london_to_nse": "DATA_INSUFFICIENT",
        "crypto_htf_stack_to_nifty_3m": "DATA_INSUFFICIENT",
        "ob_candle_combine": "DISCRETIONARY_NOT_FROZEN",
        "equal_high_epsilon": "HYPOTHESIS",
        "proxy_layer": "PROJECT_MIX_OHLC",
        "teacher_assets": "US_FUTURES_FX_CRYPTO",
    }
