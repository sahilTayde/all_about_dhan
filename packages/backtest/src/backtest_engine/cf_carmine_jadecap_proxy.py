"""Chart Fanatics Phase-8 OHLC proxies — Carmine Rosato + Jadecap.

EXTERNAL guests — not DHAN-DERIVED. Structure proxies only.
ASR transcripts — not YouTube captions. No win-rate claim. No live orders.
True Carmine OF absorb = DATA_INSUFFICIENT. Jade Asia/London sessions = DI.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from backtest_engine.clocks import minutes_ist, session_date_ist
from backtest_engine.indicators import Bar


def _is_bullish_fvg(bars: list[Bar], i: int) -> bool:
    """3-candle bullish FVG: bar i-2 high < bar i low (gap up)."""
    if i < 2:
        return False
    return bars[i - 2].high < bars[i].low


def _is_bearish_fvg(bars: list[Bar], i: int) -> bool:
    if i < 2:
        return False
    return bars[i - 2].low > bars[i].high


def lean_cf_carmine_fail_break(
    bars: list[Bar],
    *,
    confirm_bars: int = 4,
) -> list[str]:
    """Failed breakdown / stop-hunt stand-in: sweep PDH/PDL then close reclaim.

    CE = sweep prior-day low then close back above it.
    PE = sweep prior-day high then close back below it.
    No volume-tail / delta — structure only. Separate from Marco/Jade rows.
    """
    n = len(bars)
    out = ["SKIP"] * n
    daily_hi: dict[str, float] = {}
    daily_lo: dict[str, float] = {}
    by_day: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(bars):
        d = session_date_ist(b.ts)
        by_day[d].append(i)
        daily_hi[d] = max(daily_hi.get(d, b.high), b.high)
        daily_lo[d] = min(daily_lo.get(d, b.low), b.low)
    days = sorted(by_day)
    prev_hl: dict[str, tuple[float, float]] = {}
    for i, day in enumerate(days):
        if i == 0:
            continue
        pd = days[i - 1]
        prev_hl[day] = (daily_hi[pd], daily_lo[pd])

    for day, idxs in by_day.items():
        if day not in prev_hl:
            continue
        pdh, pdl = prev_hl[day]
        hi_sweep: Optional[int] = None
        lo_sweep: Optional[int] = None
        done_hi = False
        done_lo = False
        for j in idxs:
            bar = bars[j]
            if not done_hi:
                if hi_sweep is None and bar.high > pdh:
                    hi_sweep = j
                elif hi_sweep is not None and 0 < j - hi_sweep <= confirm_bars:
                    if bar.close < pdh:
                        out[j] = "PE"
                        done_hi = True
                if hi_sweep is not None and j - hi_sweep > confirm_bars:
                    hi_sweep = None
            if not done_lo:
                if lo_sweep is None and bar.low < pdl:
                    lo_sweep = j
                elif lo_sweep is not None and 0 < j - lo_sweep <= confirm_bars:
                    if bar.close > pdl and out[j] == "SKIP":
                        out[j] = "CE"
                        done_lo = True
                if lo_sweep is not None and j - lo_sweep > confirm_bars:
                    lo_sweep = None
    return out


def lean_cf_carmine_open_hold(
    bars: list[Bar],
    *,
    early_end_minute: int = 10 * 60 + 30,  # IST stand-in — not ET 9:30–10 map
    pullback_bars: int = 12,
    hold_frac: float = 0.0003,
) -> list[str]:
    """Hold session open on early pullback → CE (inverse PE).

    Teacher: aggressive sell pullback holds opening print. Proxy = structure only
    (no OF aggression). Emit after first pullback that stays above/below open.
    """
    n = len(bars)
    out = ["SKIP"] * n
    by_day: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(bars):
        by_day[session_date_ist(b.ts)].append(i)

    for idxs in by_day.values():
        if not idxs:
            continue
        open_px = bars[idxs[0]].open
        run_lo = open_px
        run_hi = open_px
        emitted = False
        for k, j in enumerate(idxs):
            m = minutes_ist(bars[j].ts)
            if m > early_end_minute or k > pullback_bars * 3:
                break
            bar = bars[j]
            if bar.low < run_lo:
                run_lo = bar.low
            if bar.high > run_hi:
                run_hi = bar.high
            if emitted or k < 2:
                continue
            # Long: dipped below open then closed back above open (hold reclaim)
            if (
                run_lo < open_px * (1.0 - hold_frac)
                and bar.close > open_px
                and bar.low >= open_px * (1.0 - hold_frac * 3)
            ):
                out[j] = "CE"
                emitted = True
            # Short: spiked above open then closed back below
            elif (
                run_hi > open_px * (1.0 + hold_frac)
                and bar.close < open_px
                and bar.high <= open_px * (1.0 + hold_frac * 3)
            ):
                out[j] = "PE"
                emitted = True
    return out


def lean_cf_jadecap_swing_fail(
    bars: list[Bar],
    *,
    confirm_bars: int = 6,
) -> list[str]:
    """Jadecap homework swing failure: raid PDH/PDL then close reclaim.

    Distinct catalog row from Carmine fail-break / Marco liq-trap (KEEP_ALL).
    """
    # Same geometric skeleton as Carmine PDH/PDL reclaim — separate book_id / recipe.
    return lean_cf_carmine_fail_break(bars, confirm_bars=confirm_bars)


def lean_cf_jadecap_fvg_draw(
    bars: list[Bar],
    *,
    confirm_bars: int = 8,
) -> list[str]:
    """After PDH/PDL sweep same day, lean into first opposing 3-candle FVG.

    CE: PDL swept, then bullish FVG forms → long stand-in.
    PE: PDH swept, then bearish FVG forms → short stand-in.
    Full ICT stack / breaker / turtle soup not modeled.
    """
    n = len(bars)
    out = ["SKIP"] * n
    daily_hi: dict[str, float] = {}
    daily_lo: dict[str, float] = {}
    by_day: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(bars):
        d = session_date_ist(b.ts)
        by_day[d].append(i)
        daily_hi[d] = max(daily_hi.get(d, b.high), b.high)
        daily_lo[d] = min(daily_lo.get(d, b.low), b.low)
    days = sorted(by_day)
    prev_hl: dict[str, tuple[float, float]] = {}
    for i, day in enumerate(days):
        if i == 0:
            continue
        pd = days[i - 1]
        prev_hl[day] = (daily_hi[pd], daily_lo[pd])

    for day, idxs in by_day.items():
        if day not in prev_hl:
            continue
        pdh, pdl = prev_hl[day]
        swept_hi = False
        swept_lo = False
        sweep_hi_i: Optional[int] = None
        sweep_lo_i: Optional[int] = None
        done = False
        for j in idxs:
            if done:
                break
            bar = bars[j]
            if not swept_hi and bar.high > pdh:
                swept_hi = True
                sweep_hi_i = j
            if not swept_lo and bar.low < pdl:
                swept_lo = True
                sweep_lo_i = j
            if swept_lo and sweep_lo_i is not None and 0 < j - sweep_lo_i <= confirm_bars:
                if _is_bullish_fvg(bars, j):
                    out[j] = "CE"
                    done = True
                    continue
            if swept_hi and sweep_hi_i is not None and 0 < j - sweep_hi_i <= confirm_bars:
                if _is_bearish_fvg(bars, j) and out[j] == "SKIP":
                    out[j] = "PE"
                    done = True
    return out


def gap_summary_carmine_jadecap() -> dict[str, str]:
    return {
        "transcript_source": "ASR_WHISPER_NOT_YT_CAPTIONS",
        "gex_option_chain": "NOT_IN_RECIPE",
        "carmine_dom_heatmap_footprint_delta": "PARKED_NO_INDIA_TAPE",
        "carmine_absorb": "DATA_INSUFFICIENT_OF_REQUIRED",
        "carmine_lvn_math": "PRIOR_EPISODE_NOT_RE_DERIVED",
        "jadecap_asia_london_ny_clocks": "DATA_INSUFFICIENT",
        "jadecap_midnight_open_multiples": "DATA_INSUFFICIENT",
        "jadecap_breaker_turtle_soup": "NAMED_NOT_FROZEN_THIS_BOOK",
        "et_session_to_nse": "DATA_INSUFFICIENT",
        "dollar_pnl_may_203k_apex_payouts": "MARKETING_NOT_PRODUCT_METRIC",
        "proxy_layer": "PROJECT_MIX_OHLC",
        "teacher_assets": "ES_NQ_NY_FX_ANECDOTE",
    }
