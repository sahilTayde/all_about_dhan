"""Chart Fanatics Phase-5 OHLC proxies — Marci Silfrain + Tori Trades.

EXTERNAL guests — not DHAN-DERIVED. Structure proxies only.
ASR transcripts — not YouTube captions. No win-rate claim. No live orders.
"""

from __future__ import annotations

from typing import Optional

from backtest_engine.indicators import Bar, sma


def _is_swing_high(bars: list[Bar], i: int) -> bool:
    if i < 1 or i >= len(bars) - 1:
        return False
    return bars[i].high >= bars[i - 1].high and bars[i].high >= bars[i + 1].high


def _is_swing_low(bars: list[Bar], i: int) -> bool:
    if i < 1 or i >= len(bars) - 1:
        return False
    return bars[i].low <= bars[i - 1].low and bars[i].low <= bars[i + 1].low


def _stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5


def lean_cf_marci_rizzy_ext(
    bars: list[Bar],
    *,
    lookback: int = 40,
) -> list[str]:
    """Little-rizzie measured-move structure proxy (no hand-drawn TL).

    PE: swing high H1, intervening low L, later swing high H2 < H1 → lean short
        when price turns down from H2 (close below midpoint of L..H2).
    CE: inverse higher-low pattern.
    """
    n = len(bars)
    out = ["SKIP"] * n
    for i in range(4, n):
        # Confirm swing at i-2
        mid = i - 2
        if mid < 2:
            continue
        start = max(1, mid - lookback)

        if _is_swing_high(bars, mid):
            # Find prior higher swing high and intervening low
            prior_hi_i: Optional[int] = None
            for j in range(mid - 2, start - 1, -1):
                if _is_swing_high(bars, j) and bars[j].high > bars[mid].high:
                    prior_hi_i = j
                    break
            if prior_hi_i is None:
                continue
            lo = min(b.low for b in bars[prior_hi_i : mid + 1])
            mid_px = 0.5 * (lo + bars[mid].high)
            if bars[i].close < mid_px and out[i] == "SKIP":
                out[i] = "PE"

        if _is_swing_low(bars, mid):
            prior_lo_i: Optional[int] = None
            for j in range(mid - 2, start - 1, -1):
                if _is_swing_low(bars, j) and bars[j].low < bars[mid].low:
                    prior_lo_i = j
                    break
            if prior_lo_i is None:
                continue
            hi = max(b.high for b in bars[prior_lo_i : mid + 1])
            mid_px = 0.5 * (hi + bars[mid].low)
            if bars[i].close > mid_px and out[i] == "SKIP":
                out[i] = "CE"

    return out


def lean_cf_marci_bb_reality(
    bars: list[Bar],
    *,
    length: int = 20,
    k: float = 2.0,
    touch_lookback: int = 30,
) -> list[str]:
    """BB 2σ 'reality' proxy: reclaim mid after outer-band touch.

    CE: touched lower band recently, then close crosses above mid.
    PE: touched upper band recently, then close crosses below mid.
    Guest rizzie TL not modeled — location/mean-reversion stand-in only.
    """
    n = len(bars)
    out = ["SKIP"] * n
    closes = [b.close for b in bars]
    mid = sma(closes, length)
    last_upper_touch: Optional[int] = None
    last_lower_touch: Optional[int] = None

    for i in range(n):
        m = mid[i]
        if m is None or i + 1 < length:
            continue
        sd = _stdev(closes[i + 1 - length : i + 1])
        up, dn = m + k * sd, m - k * sd
        bar = bars[i]
        if bar.high >= up:
            last_upper_touch = i
        if bar.low <= dn:
            last_lower_touch = i

        if (
            last_lower_touch is not None
            and 0 < i - last_lower_touch <= touch_lookback
            and i > 0
            and bars[i - 1].close <= m
            and bar.close > m
        ):
            out[i] = "CE"
            last_lower_touch = None
        elif (
            last_upper_touch is not None
            and 0 < i - last_upper_touch <= touch_lookback
            and i > 0
            and bars[i - 1].close >= m
            and bar.close < m
        ):
            out[i] = "PE"
            last_upper_touch = None

    return out


def _line_at(i0: int, p0: float, i1: int, p1: float, i: int) -> float:
    if i1 == i0:
        return p0
    t = (i - i0) / (i1 - i0)
    return p0 + t * (p1 - p0)


def lean_cf_tori_tl_bounce(
    bars: list[Bar],
    *,
    lookback: int = 60,
    touch_frac: float = 0.0015,
    min_span: int = 8,
) -> list[str]:
    """Trendline bounce proxy: tag extrapolated swing line then close back.

    CE: ≥2 ascending swing lows; price low near line; close above line.
    PE: ≥2 descending swing highs; price high near line; close below line.
    Thick-line / week-data / alert workflow not modeled.
    """
    n = len(bars)
    out = ["SKIP"] * n
    for i in range(5, n):
        start = max(1, i - lookback)
        lows: list[tuple[int, float]] = []
        highs: list[tuple[int, float]] = []
        for j in range(start, i - 1):
            if _is_swing_low(bars, j):
                lows.append((j, bars[j].low))
            if _is_swing_high(bars, j):
                highs.append((j, bars[j].high))

        if len(lows) >= 2:
            a, b = lows[-2], lows[-1]
            if b[0] - a[0] >= min_span and b[1] > a[1]:
                lvl = _line_at(a[0], a[1], b[0], b[1], i)
                if lvl > 0 and abs(bars[i].low - lvl) / lvl <= touch_frac and bars[i].close > lvl:
                    out[i] = "CE"

        if len(highs) >= 2 and out[i] == "SKIP":
            a, b = highs[-2], highs[-1]
            if b[0] - a[0] >= min_span and b[1] < a[1]:
                lvl = _line_at(a[0], a[1], b[0], b[1], i)
                if lvl > 0 and abs(bars[i].high - lvl) / lvl <= touch_frac and bars[i].close < lvl:
                    out[i] = "PE"

    return out


def lean_cf_tori_tl_break(
    bars: list[Bar],
    *,
    lookback: int = 60,
    min_touches: int = 2,
    min_span: int = 8,
    safety_frac: float = 0.01,
) -> list[str]:
    """Trendline break + opposing safety nearby (low-risk gate proxy).

    PE: break below ascending multi-touch swing-low line while a descending
        swing-high line exists within safety_frac of price.
    CE: inverse.
    Fan pivots / discretionary conviction / 4H week filter not modeled.
    """
    n = len(bars)
    out = ["SKIP"] * n
    for i in range(8, n):
        start = max(1, i - lookback)
        lows: list[tuple[int, float]] = []
        highs: list[tuple[int, float]] = []
        for j in range(start, i - 1):
            if _is_swing_low(bars, j):
                lows.append((j, bars[j].low))
            if _is_swing_high(bars, j):
                highs.append((j, bars[j].high))

        # Break of ascending support → PE if opposing descending resistance nearby
        if len(lows) >= min_touches:
            a, b = lows[-2], lows[-1]
            if b[0] - a[0] >= min_span and b[1] > a[1]:
                lvl = _line_at(a[0], a[1], b[0], b[1], i)
                prev = _line_at(a[0], a[1], b[0], b[1], i - 1)
                if bars[i - 1].close >= prev and bars[i].close < lvl and lvl > 0:
                    # Need opposing descending highs as safety
                    if len(highs) >= 2:
                        ha, hb = highs[-2], highs[-1]
                        if hb[1] < ha[1]:
                            safety = _line_at(ha[0], ha[1], hb[0], hb[1], i)
                            if safety > 0 and abs(bars[i].close - safety) / safety <= safety_frac:
                                out[i] = "PE"

        if len(highs) >= min_touches and out[i] == "SKIP":
            a, b = highs[-2], highs[-1]
            if b[0] - a[0] >= min_span and b[1] < a[1]:
                lvl = _line_at(a[0], a[1], b[0], b[1], i)
                prev = _line_at(a[0], a[1], b[0], b[1], i - 1)
                if bars[i - 1].close <= prev and bars[i].close > lvl and lvl > 0:
                    if len(lows) >= 2:
                        la, lb = lows[-2], lows[-1]
                        if lb[1] > la[1]:
                            safety = _line_at(la[0], la[1], lb[0], lb[1], i)
                            if safety > 0 and abs(bars[i].close - safety) / safety <= safety_frac:
                                out[i] = "CE"

    return out


def gap_summary_marci_tori() -> dict[str, str]:
    return {
        "transcript_source": "ASR_WHISPER_NOT_YT_CAPTIONS",
        "gex_option_chain": "NOT_IN_RECIPE",
        "order_flow": "NOT_REQUIRED_BY_GUESTS",
        "ny_open_avoid_to_nse": "DATA_INSUFFICIENT",
        "h4_week_data_to_nifty_3m": "DATA_INSUFFICIENT",
        "little_rizzie_hand_tl": "DISCRETIONARY_NOT_FROZEN",
        "tori_thick_line_breathing_room": "DISCRETIONARY_NOT_FROZEN",
        "bb_period": "HYPOTHESIS_20",
        "proxy_layer": "PROJECT_MIX_OHLC",
        "teacher_assets": "US_INDEX_BTC_EQUITY_COMMODITY_FUTURES",
    }
