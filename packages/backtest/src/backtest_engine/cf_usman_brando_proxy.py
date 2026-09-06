"""Chart Fanatics Phase-9 OHLC proxies — Usman Ashraf + Brando/Leaf.

EXTERNAL guests — not DHAN-DERIVED. Options recipes mostly DI.
ASR transcripts — not YouTube captions. No win-rate claim. No live orders.
Usman OI/greeks/weekly-size/price-stop = DATA_INSUFFICIENT without OPTIDX.
Brando news-align + size-zero = DATA_INSUFFICIENT. Structure proxies only for
HTF reclaim / round-break / HTF bounce.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from backtest_engine.indicators import Bar
from backtest_engine.clocks import session_date_ist


def lean_cf_brando_htf_reclaim(
    bars: list[Bar],
    *,
    swing_days: int = 20,
    confirm_bars: int = 8,
) -> list[str]:
    """HTF major-level reclaim stand-in: sweep prior multi-day swing then reclaim.

    CE = sweep prior `swing_days` low then close back above it.
    PE = sweep prior `swing_days` high then close back below it.
    Not multi-year SPX 'major'; no news. Separate from Carmine/Jade PDH/PDL.
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
    if len(days) < swing_days + 1:
        return out

    for di, day in enumerate(days):
        if di < swing_days:
            continue
        prev = days[di - swing_days : di]
        swing_hi = max(daily_hi[d] for d in prev)
        swing_lo = min(daily_lo[d] for d in prev)
        hi_sweep: Optional[int] = None
        lo_sweep: Optional[int] = None
        done_hi = False
        done_lo = False
        for j in by_day[day]:
            bar = bars[j]
            if not done_hi:
                if hi_sweep is None and bar.high > swing_hi:
                    hi_sweep = j
                elif hi_sweep is not None and 0 < j - hi_sweep <= confirm_bars:
                    if bar.close < swing_hi:
                        out[j] = "PE"
                        done_hi = True
                if hi_sweep is not None and j - hi_sweep > confirm_bars:
                    hi_sweep = None
            if not done_lo:
                if lo_sweep is None and bar.low < swing_lo:
                    lo_sweep = j
                elif lo_sweep is not None and 0 < j - lo_sweep <= confirm_bars:
                    if bar.close > swing_lo and out[j] == "SKIP":
                        out[j] = "CE"
                        done_lo = True
                if lo_sweep is not None and j - lo_sweep > confirm_bars:
                    lo_sweep = None
    return out


def lean_cf_brando_round_break(
    bars: list[Bar],
    *,
    round_step: float = 100.0,
    confirm_bars: int = 3,
) -> list[str]:
    """Round-number break stand-in (NIFTY 100-pt grid).

    CE = close above round that prior bar was at/below.
    PE = close below round that prior bar was at/above.
    No Fed/tariff catalyst — structure only.
    """
    n = len(bars)
    out = ["SKIP"] * n
    if n < 5 or round_step <= 0:
        return out

    def _round_levels(px: float) -> list[float]:
        base = (px // round_step) * round_step
        return [base - round_step, base, base + round_step, base + 2 * round_step]

    last_emit_day: Optional[str] = None
    for i in range(1, n):
        prev = bars[i - 1]
        bar = bars[i]
        day = session_date_ist(bar.ts)
        if last_emit_day == day:
            continue
        for lvl in _round_levels(prev.close):
            # break up
            if prev.close <= lvl < bar.close:
                # mild confirm: next bars not instantly reverse — emit now
                out[i] = "CE"
                last_emit_day = day
                break
            # break down
            if prev.close >= lvl > bar.close:
                out[i] = "PE"
                last_emit_day = day
                break
        _ = confirm_bars  # reserved for future ADD grid
    return out


def lean_cf_brando_htf_bounce(
    bars: list[Bar],
    *,
    swing_lookback: int = 60,
    touch_frac: float = 0.0015,
    bounce_frac: float = 0.0020,
) -> list[str]:
    """HTF defend/bounce stand-in: touch prior swing then strong close away.

    CE = touch swing low within touch_frac then close up by bounce_frac.
    PE = touch swing high within touch_frac then close down by bounce_frac.
    """
    n = len(bars)
    out = ["SKIP"] * n
    if n < swing_lookback + 5:
        return out

    last_emit_day: Optional[str] = None
    for i in range(swing_lookback, n):
        day = session_date_ist(bars[i].ts)
        if last_emit_day == day:
            continue
        window = bars[i - swing_lookback : i]
        swing_hi = max(b.high for b in window)
        swing_lo = min(b.low for b in window)
        bar = bars[i]
        # support bounce
        if bar.low <= swing_lo * (1.0 + touch_frac) and bar.low >= swing_lo * (
            1.0 - touch_frac
        ):
            if bar.close >= swing_lo * (1.0 + bounce_frac):
                out[i] = "CE"
                last_emit_day = day
                continue
        # resistance reject
        if bar.high >= swing_hi * (1.0 - touch_frac) and bar.high <= swing_hi * (
            1.0 + touch_frac
        ):
            if bar.close <= swing_hi * (1.0 - bounce_frac):
                out[i] = "PE"
                last_emit_day = day
    return out


def gap_summary_usman_brando() -> dict[str, str]:
    return {
        "transcript_source": "ASR_WHISPER_NOT_YT_CAPTIONS",
        "gex_option_chain": "NOT_IN_RECIPE",
        "usman_guest_asr": "Osman_Astra_UNKNOWN_to_Usman_Ashraf",
        "brando_guest_asr": "brand_a_k_a_leaf_UNKNOWN_to_Brando_Leaf",
        "usman_oi_volume_chain": "DATA_INSUFFICIENT_NO_OPTIDX_OI_BOOK",
        "usman_0dte_gamma_iv": "DATA_INSUFFICIENT_NO_GREEKS",
        "usman_weekly_size": "DATA_INSUFFICIENT_MANAGEMENT_PREMIUM",
        "usman_price_stop": "DATA_INSUFFICIENT_ENTRY_LOI_NOT_FROZEN",
        "us_friday_0dte_to_nifty_weekly": "DATA_INSUFFICIENT",
        "brando_news_fed_tariff": "DATA_INSUFFICIENT_NO_NEWS_JOIN",
        "brando_size_zero": "DATA_INSUFFICIENT_PREMIUM_LEDGER",
        "brando_spx_major_multiyear": "PROXY_SWING_LOOKBACK_ONLY",
        "title_6k_to_10m_80pct_rhetoric": "MARKETING_NOT_PRODUCT_METRIC",
        "proxy_layer": "PROJECT_MIX_OHLC",
        "teacher_assets": "US_EQUITY_OPTIONS_SPX",
    }
