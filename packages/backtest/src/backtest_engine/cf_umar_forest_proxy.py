"""Chart Fanatics Phase-7 OHLC proxies — Umar Ashraf + Forest Knight.

EXTERNAL guests — not DHAN-DERIVED. Structure / bar-volume proxies only.
ASR transcripts — not YouTube captions. No win-rate claim. No live orders.
Opening-drive = DATA_INSUFFICIENT (named only). True VAP / OF tape not claimed.
"""

from __future__ import annotations

from collections import defaultdict

from backtest_engine.clocks import minutes_ist, session_date_ist
from backtest_engine.fabio_proxy import prior_session_profile
from backtest_engine.indicators import Bar


def _is_doji(bar: Bar, *, max_body_frac: float = 0.35) -> bool:
    rng = bar.high - bar.low
    if rng <= 0:
        return False
    return abs(bar.close - bar.open) / rng <= max_body_frac


def _is_hammer(bar: Bar, *, min_wick_frac: float = 0.55) -> bool:
    rng = bar.high - bar.low
    if rng <= 0:
        return False
    body_top = max(bar.open, bar.close)
    body_bot = min(bar.open, bar.close)
    lower = body_bot - bar.low
    upper = bar.high - body_top
    return lower / rng >= min_wick_frac and upper / rng <= 0.25


def _is_shooting_star(bar: Bar, *, min_wick_frac: float = 0.55) -> bool:
    rng = bar.high - bar.low
    if rng <= 0:
        return False
    body_top = max(bar.open, bar.close)
    body_bot = min(bar.open, bar.close)
    upper = bar.high - body_top
    lower = body_bot - bar.low
    return upper / rng >= min_wick_frac and lower / rng <= 0.25


def _rel_vol_up(bars: list[Bar], i: int) -> bool:
    if i < 1:
        return False
    prev = bars[i - 1].volume
    cur = bars[i].volume
    if prev <= 0 and cur <= 0:
        # equal-weight stand-in: treat as relative if range expands
        return (bars[i].high - bars[i].low) > (bars[i - 1].high - bars[i - 1].low)
    return cur > prev


def lean_cf_umar_morning_top(
    bars: list[Bar],
    *,
    gap_frac: float = 0.0015,
    early_start_minute: int = 9 * 60 + 45,  # after STRAT-009 open skip (NSE stand-in)
    early_end_minute: int = 11 * 60 + 0,  # IST stand-in for morning window — not ET map
    bounce_look: int = 16,
) -> list[str]:
    """Gap-down + early failed bounce → PE (morning top stand-in).

    CE inverse: gap-up + failed early dump (not fully taught — optional symmetry).
    OF tape / 9:30–11 ET not modeled — NSE clock stand-in only.
    Emit only after 09:45 IST so 009 open-skip does not zero the book.
    """
    n = len(bars)
    out = ["SKIP"] * n
    by_day: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(bars):
        by_day[session_date_ist(b.ts)].append(i)
    days = sorted(by_day)
    prev_close: dict[str, float] = {}
    for i, day in enumerate(days):
        idxs = by_day[day]
        prev_close[day] = bars[idxs[-1]].close
        if i == 0:
            continue
        pdc = prev_close[days[i - 1]]
        first_i = idxs[0]
        open_px = bars[first_i].open
        # Gap down morning top
        if open_px < pdc * (1.0 - gap_frac):
            run_hi = open_px
            emitted = False
            for k, j in enumerate(idxs):
                m = minutes_ist(bars[j].ts)
                if m > early_end_minute:
                    break
                if bars[j].high > run_hi:
                    run_hi = bars[j].high
                if m < early_start_minute:
                    continue
                if k > bounce_look * 3:
                    break
                if (
                    not emitted
                    and run_hi > open_px
                    and bars[j].close < open_px
                    and bars[j].high < run_hi
                ):
                    out[j] = "PE"
                    emitted = True
                    break
        # Gap up weak dump reclaim → CE (symmetry; not A+ taught)
        elif open_px > pdc * (1.0 + gap_frac):
            run_lo = open_px
            emitted = False
            for k, j in enumerate(idxs):
                m = minutes_ist(bars[j].ts)
                if m > early_end_minute:
                    break
                if bars[j].low < run_lo:
                    run_lo = bars[j].low
                if m < early_start_minute:
                    continue
                if k > bounce_look * 3:
                    break
                if (
                    not emitted
                    and run_lo < open_px
                    and bars[j].close > open_px
                    and bars[j].low > run_lo
                ):
                    out[j] = "CE"
                    emitted = True
                    break
    return out


def lean_cf_forest_vpe_edge(
    bars: list[Bar],
    *,
    touch_frac: float = 0.0015,
) -> list[str]:
    """PDH/PDL touch + relative-volume rejection candle (VPE edge stand-in).

    Overnight H/L not modeled (DI). True HVN shelf = DI — prior day extremes only.
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

    for i in range(1, n):
        day = session_date_ist(bars[i].ts)
        if day not in prev_hl:
            continue
        pdh, pdl = prev_hl[day]
        bar = bars[i]
        if not _rel_vol_up(bars, i):
            continue
        # PE: tag PDH with shooting star / doji close back
        if bar.high >= pdh * (1.0 - touch_frac) and (
            _is_shooting_star(bar) or (_is_doji(bar) and bar.close < bar.open)
        ):
            out[i] = "PE"
        # CE: tag PDL with hammer / doji close up
        elif bar.low <= pdl * (1.0 + touch_frac) and (
            _is_hammer(bar) or (_is_doji(bar) and bar.close > bar.open)
        ):
            out[i] = "CE"
    return out


def lean_cf_forest_poc_retest(
    bars: list[Bar],
    *,
    touch_frac: float = 0.002,
    trend_look: int = 20,
) -> list[str]:
    """Prior-session bin POC/VAL touch with trend filter (POC retest stand-in).

    Reuses fabio_proxy.prior_session_profile — PROJECT bins, not exchange VAP.
    """
    profile = prior_session_profile(bars)
    n = len(bars)
    out = ["SKIP"] * n
    closes = [b.close for b in bars]
    for i in range(trend_look, n):
        day = session_date_ist(bars[i].ts)
        prof = profile.get(day)
        if not prof:
            continue
        poc = float(prof["poc"])
        val = float(prof["val"])
        vah = float(prof["vah"])
        bar = bars[i]
        trend_up = closes[i - 1] > closes[i - 1 - trend_look]
        trend_dn = closes[i - 1] < closes[i - 1 - trend_look]
        near_poc = abs(bar.low - poc) / poc <= touch_frac or abs(bar.high - poc) / poc <= touch_frac
        near_val = abs(bar.low - val) / max(val, 1e-9) <= touch_frac
        near_vah = abs(bar.high - vah) / max(vah, 1e-9) <= touch_frac
        if trend_up and (near_poc or near_val) and bar.close >= min(bar.open, poc):
            out[i] = "CE"
        elif trend_dn and (near_poc or near_vah) and bar.close <= max(bar.open, poc):
            out[i] = "PE"
    return out


def gap_summary_umar_forest() -> dict[str, str]:
    return {
        "transcript_source": "ASR_WHISPER_NOT_YT_CAPTIONS",
        "gex_option_chain": "NOT_IN_RECIPE",
        "umar_of_tape": "TEACHER_PREFERRED_PROXY_OHLC_ONLY",
        "umar_opening_drive": "DATA_INSUFFICIENT_NAMED_ONLY",
        "umar_guest_asr_name": "Buma_Ashraf_UNKNOWN",
        "forest_true_vap": "PROJECT_BIN_PROXY_NOT_EXCHANGE_VAP",
        "forest_overnight_hl": "DATA_INSUFFICIENT",
        "et_session_to_nse": "DATA_INSUFFICIENT",
        "index_volume_quality": "UNKNOWN_EQUAL_WEIGHT_FALLBACK",
        "rhetoric_100pct_react": "MARKETING_NOT_PRODUCT_METRIC",
        "proxy_layer": "PROJECT_MIX_OHLC",
        "teacher_assets": "ES_NQ_SPX_OI_ANALOGY",
    }
