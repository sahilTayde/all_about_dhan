"""Chart Fanatics Phase-10 OHLC proxies — Andrea Cimi + Omor/NBB.

EXTERNAL guests — not DHAN-DERIVED. Structure proxies only.
ASR transcripts — not YouTube captions. No win-rate claim. No live orders.
Andrea true OF absorb = DATA_INSUFFICIENT/PARKED. Omor KZ/ADR = DI.
Do NOT merge Andrea into MIX-CF-FABIO-*.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from backtest_engine.clocks import minutes_ist, session_date_ist
from backtest_engine.indicators import Bar


def lean_cf_andrea_fail_auction(
    bars: list[Bar],
    *,
    confirm_bars: int = 6,
) -> list[str]:
    """Failed-auction / VA ping-pong stand-in: pierce prior-day range then reclaim mid.

    CE = sweep prior-day low then close back above mid of prior-day range.
    PE = sweep prior-day high then close back below mid.
    No volume-profile VA; no absorb tape — structure only.
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
        mid = 0.5 * (pdh + pdl)
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
                    if bar.close < mid:
                        out[j] = "PE"
                        done_hi = True
                if hi_sweep is not None and j - hi_sweep > confirm_bars:
                    hi_sweep = None
            if not done_lo:
                if lo_sweep is None and bar.low < pdl:
                    lo_sweep = j
                elif lo_sweep is not None and 0 < j - lo_sweep <= confirm_bars:
                    if bar.close > mid and out[j] == "SKIP":
                        out[j] = "CE"
                        done_lo = True
                if lo_sweep is not None and j - lo_sweep > confirm_bars:
                    lo_sweep = None
    return out


def lean_cf_andrea_orb_accept(
    bars: list[Bar],
    *,
    orb_end_minute: int = 9 * 60 + 45,  # IST stand-in — not NY open map
    confirm_bars: int = 2,
    hold_frac: float = 0.0002,
) -> list[str]:
    """ORB acceptance stand-in: break first-session OR and hold outside.

    No OF acceptance / bubbles — close beyond OR + confirm holds only.
    """
    n = len(bars)
    out = ["SKIP"] * n
    by_day: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(bars):
        by_day[session_date_ist(b.ts)].append(i)

    for idxs in by_day.values():
        if len(idxs) < 8:
            continue
        or_hi = float("-inf")
        or_lo = float("inf")
        or_end_i: Optional[int] = None
        for j in idxs:
            m = minutes_ist(bars[j].ts)
            if m <= orb_end_minute:
                or_hi = max(or_hi, bars[j].high)
                or_lo = min(or_lo, bars[j].low)
                or_end_i = j
            else:
                break
        if or_end_i is None or or_hi <= or_lo:
            continue
        emitted = False
        pending: Optional[str] = None
        pending_i: Optional[int] = None
        for j in idxs:
            if j <= or_end_i or emitted:
                continue
            bar = bars[j]
            if pending is None:
                if bar.close > or_hi * (1.0 + hold_frac):
                    pending, pending_i = "CE", j
                elif bar.close < or_lo * (1.0 - hold_frac):
                    pending, pending_i = "PE", j
                continue
            assert pending_i is not None
            if j - pending_i > confirm_bars:
                pending = None
                pending_i = None
                continue
            if pending == "CE" and bar.close >= or_hi:
                out[j] = "CE"
                emitted = True
            elif pending == "PE" and bar.close <= or_lo:
                out[j] = "PE"
                emitted = True
    return out


def lean_cf_andrea_stop_fade(
    bars: list[Bar],
    *,
    confirm_bars: int = 3,
) -> list[str]:
    """Stop-run fade stand-in: sweep PDH/PDL then quick close back through level.

    Distinct from fail-auction mid-target: fade back across the extreme only.
    No cascade tape. Teacher: short fade ≠ full-day reverse.
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


def lean_cf_omor_mmm_frame(
    bars: list[Bar],
    *,
    confirm_bars: int = 5,
    body_frac: float = 0.55,
) -> list[str]:
    """MMM/PO3 framework stand-in: prior-day bias + PDH/PDL sweep + displace close.

    Bearish bias (prior close < prior open): PE after PDH sweep + bearish body close.
    Bullish bias: CE after PDL sweep + bullish body close.
    """
    n = len(bars)
    out = ["SKIP"] * n
    daily_hi: dict[str, float] = {}
    daily_lo: dict[str, float] = {}
    daily_open: dict[str, float] = {}
    daily_close: dict[str, float] = {}
    by_day: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(bars):
        d = session_date_ist(b.ts)
        by_day[d].append(i)
        daily_hi[d] = max(daily_hi.get(d, b.high), b.high)
        daily_lo[d] = min(daily_lo.get(d, b.low), b.low)
        if d not in daily_open:
            daily_open[d] = b.open
        daily_close[d] = b.close
    days = sorted(by_day)

    for di, day in enumerate(days):
        if di < 1:
            continue
        pd = days[di - 1]
        bias_bull = daily_close[pd] >= daily_open[pd]
        pdh, pdl = daily_hi[pd], daily_lo[pd]
        hi_sweep: Optional[int] = None
        lo_sweep: Optional[int] = None
        done = False
        for j in by_day[day]:
            if done:
                break
            bar = bars[j]
            rng = bar.high - bar.low
            body = abs(bar.close - bar.open)
            strong = rng > 0 and body / rng >= body_frac
            if not bias_bull:
                if hi_sweep is None and bar.high > pdh:
                    hi_sweep = j
                elif hi_sweep is not None and 0 < j - hi_sweep <= confirm_bars:
                    if strong and bar.close < bar.open and bar.close < pdh:
                        out[j] = "PE"
                        done = True
                if hi_sweep is not None and j - hi_sweep > confirm_bars:
                    hi_sweep = None
            else:
                if lo_sweep is None and bar.low < pdl:
                    lo_sweep = j
                elif lo_sweep is not None and 0 < j - lo_sweep <= confirm_bars:
                    if strong and bar.close > bar.open and bar.close > pdl:
                        out[j] = "CE"
                        done = True
                if lo_sweep is not None and j - lo_sweep > confirm_bars:
                    lo_sweep = None
    return out


def lean_cf_omor_ote(
    bars: list[Bar],
    *,
    swing_lookback: int = 20,
    ote_lo: float = 0.58,
    ote_hi: float = 0.66,
) -> list[str]:
    """OTE ~62% retrace stand-in after a local swing.

    After swing high→low, CE when price revisits ~62% up from low toward high.
    After swing low→high, PE when price revisits ~62% down from high toward low.
    One signal per day max. Swing grading discretionary — weak proxy.
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
        # find last swing extremes in window
        hi_i = max(range(len(window)), key=lambda k: window[k].high)
        lo_i = min(range(len(window)), key=lambda k: window[k].low)
        swing_hi = window[hi_i].high
        swing_lo = window[lo_i].low
        rng = swing_hi - swing_lo
        if rng <= 0:
            continue
        bar = bars[i]
        # distribution down then OTE long into discount of bear swing? Teacher sells in premium.
        # Bearish distribution: high then low (hi before lo) → PE at 62% retrace up
        if hi_i < lo_i:
            lvl = swing_lo + ote_lo * rng
            lvl2 = swing_lo + ote_hi * rng
            if lvl <= bar.high and bar.low <= lvl2 and bar.close < bar.open:
                out[i] = "PE"
                last_emit_day = day
        # Bullish distribution: low then high → CE at 62% retrace down
        elif lo_i < hi_i:
            lvl = swing_hi - ote_hi * rng
            lvl2 = swing_hi - ote_lo * rng
            if lvl <= bar.high and bar.low <= lvl2 and bar.close > bar.open:
                out[i] = "CE"
                last_emit_day = day
    return out


def lean_cf_omor_pdh_reversal(
    bars: list[Bar],
    *,
    near_frac: float = 0.0015,
    confirm_bars: int = 6,
) -> list[str]:
    """Open-near PDH/PDL + sweep reverse stand-in.

    Require session open within near_frac of PDH or PDL; then sweep that level
    and close back through for reverse signal.
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

    for di, day in enumerate(days):
        if di < 1:
            continue
        pd = days[di - 1]
        pdh, pdl = daily_hi[pd], daily_lo[pd]
        idxs = by_day[day]
        if not idxs:
            continue
        open_px = bars[idxs[0]].open
        near_hi = abs(open_px - pdh) / pdh <= near_frac if pdh else False
        near_lo = abs(open_px - pdl) / pdl <= near_frac if pdl else False
        if not near_hi and not near_lo:
            continue
        hi_sweep: Optional[int] = None
        lo_sweep: Optional[int] = None
        done = False
        for j in idxs:
            if done:
                break
            bar = bars[j]
            if near_hi:
                if hi_sweep is None and bar.high > pdh:
                    hi_sweep = j
                elif hi_sweep is not None and 0 < j - hi_sweep <= confirm_bars:
                    if bar.close < pdh:
                        out[j] = "PE"
                        done = True
                if hi_sweep is not None and j - hi_sweep > confirm_bars:
                    hi_sweep = None
            if near_lo and not done:
                if lo_sweep is None and bar.low < pdl:
                    lo_sweep = j
                elif lo_sweep is not None and 0 < j - lo_sweep <= confirm_bars:
                    if bar.close > pdl:
                        out[j] = "CE"
                        done = True
                if lo_sweep is not None and j - lo_sweep > confirm_bars:
                    lo_sweep = None
    return out


def gap_summary_andrea_omor() -> dict[str, str]:
    return {
        "transcript_source": "ASR_WHISPER_NOT_YT_CAPTIONS",
        "gex_option_chain": "NOT_IN_RECIPE",
        "andrea_guest_asr": "Andrea_Chimney_UNKNOWN_to_Andrea_Cimi",
        "omor_guest_asr": "Omore_MBB_UNKNOWN_to_Omor_NBB",
        "andrea_not_fabio": "DO_NOT_MERGE_MIX_CF_FABIO",
        "andrea_true_of_absorb": "DATA_INSUFFICIENT_OF_PARKED",
        "andrea_volume_profile_va": "PROXY_PRIOR_DAY_RANGE_ONLY",
        "andrea_orb_ny_clock": "IST_STANDIN_DATA_INSUFFICIENT",
        "andrea_70pct_va_8of10_fade": "MARKETING_OR_TEACHER_ANECDOTE_NOT_PRODUCT_METRIC",
        "omor_kz_london_ny": "DATA_INSUFFICIENT_NO_IST_MAP",
        "omor_adr5_session_profile": "DATA_INSUFFICIENT_WITHOUT_KZ",
        "omor_true_smt_fx": "DATA_INSUFFICIENT_SINGLE_NIFTY",
        "omor_30m_1_1m_payout_rhetoric": "MARKETING_NOT_PRODUCT_METRIC",
        "proxy_layer": "PROJECT_MIX_OHLC",
        "teacher_assets": "ES_FUTURES_AND_FX_ICT",
    }
