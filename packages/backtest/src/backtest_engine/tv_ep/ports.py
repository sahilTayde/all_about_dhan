"""Public-rule Python ports for MIX-TV-EP-001..023. No Pine source in this file.

Leans are CE / PE / HOLD for the existing next-bar-open simulator.
TV SL/TP/qty/commission are HYPOTHESIS notes on the adapter, not Dhan fields.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from backtest_engine.clocks import session_date_ist
from backtest_engine.indicators import (
    Bar,
    _wilder_atr,
    ema,
    macd_hist,
    rsi,
    sma,
    wma,
)


def _cross_up(a: Optional[float], b: Optional[float], ap: Optional[float], bp: Optional[float]) -> bool:
    if None in (a, b, ap, bp):
        return False
    return ap <= bp and a > b  # type: ignore[operator]


def _cross_dn(a: Optional[float], b: Optional[float], ap: Optional[float], bp: Optional[float]) -> bool:
    if None in (a, b, ap, bp):
        return False
    return ap >= bp and a < b  # type: ignore[operator]


def _ma(values: list[float], length: int, kind: str) -> list[float | None]:
    k = (kind or "sma").lower()
    if k == "ema":
        return ema(values, length)
    if k == "wma":
        return wma(values, length)
    return sma(values, length)


def _ma_cross_leans(
    bars: list[Bar],
    params: dict[str, float],
    *,
    fast_key: str = "fast",
    slow_key: str = "slow",
    fast_default: int = 14,
    slow_default: int = 28,
    kind: str = "sma",
    long_only: bool = False,
) -> list[str]:
    closes = [b.close for b in bars]
    fast_n = int(params.get(fast_key, params.get("fast", fast_default)))
    slow_n = int(params.get(slow_key, params.get("slow", slow_default)))
    kind = str(params.get("ma_type", kind) or kind)
    fast = _ma(closes, max(1, fast_n), kind)
    slow = _ma(closes, max(1, slow_n), kind)
    leans = ["HOLD"] * len(bars)
    for i in range(1, len(bars)):
        if _cross_up(fast[i], slow[i], fast[i - 1], slow[i - 1]):
            leans[i] = "CE"
        elif _cross_dn(fast[i], slow[i], fast[i - 1], slow[i - 1]):
            # Long-only: record sell/flat as EXIT (counted), never equity short.
            leans[i] = "EXIT" if long_only else "PE"
    return leans


def _utc(ts: int) -> datetime:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc)


def ag_sell(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-001 Kaufman Ag Selling Model: short when high >= SMA + ATR*factor in sale window."""
    ma_len = int(params.get("MA_length", 40))
    atr_len = int(params.get("ATR_length", 20))
    factor = float(params.get("ATR_factor", 2.5))
    harvest = int(params.get("Month_of_harvest", 11))
    delay = int(params.get("Delay_in_months_after_harvest", 2))
    d_between = int(params.get("Days_between_trades", 30))
    closes = [b.close for b in bars]
    trend = sma(closes, ma_len)
    atrs = _wilder_atr(bars, atr_len)
    begin = (harvest + delay) % 12
    if begin == 0:
        begin = 12
    leans = ["HOLD"] * len(bars)
    last_sale_i: Optional[int] = None
    for i, bar in enumerate(bars):
        month = datetime.fromtimestamp(bar.ts, tz=timezone.utc).month
        in_sale = month == begin or (begin < harvest and begin <= month < harvest) or (
            begin > harvest and (month >= begin or month < harvest)
        )
        # Faithful: active from beginSaleMonth until next harvest month.
        if harvest < begin:
            in_sale = month >= begin or month < harvest
        else:
            in_sale = begin <= month < harvest if begin != harvest else month != harvest
        tr, atr = trend[i], atrs[i]
        if not in_sale or tr is None or atr is None:
            if not in_sale:
                leans[i] = "CE"  # cover shorts → simulator exit via opposite
            continue
        sell_lvl = tr + atr * factor
        cooldown_ok = last_sale_i is None or (i - last_sale_i) >= max(1, d_between)
        if bar.high >= sell_lvl and cooldown_ok:
            leans[i] = "PE"
            last_sale_i = i
    return leans


def one_pct_week(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-002 TQQQ weekly: Mon open, buy 1% dip, Fri flatten. dip_pct default 1."""
    dip = float(params.get("dip_pct", 1.0)) / 100.0
    target = float(params.get("target_pct", 1.0)) / 100.0
    leans = ["HOLD"] * len(bars)
    week_open: Optional[float] = None
    in_long = False
    entry_px = 0.0
    for i, bar in enumerate(bars):
        dt = datetime.fromtimestamp(bar.ts, tz=timezone.utc)
        # IST weekday for NSE; fixture timestamps are IST-offset epoch.
        local = datetime.fromtimestamp(bar.ts, tz=timezone.utc)
        dow = datetime.fromtimestamp(bar.ts).weekday()  # 0=Mon local machine; tests use IST-aware ts
        try:
            from zoneinfo import ZoneInfo

            local = datetime.fromtimestamp(bar.ts, tz=ZoneInfo("Asia/Kolkata"))
            dow = local.weekday()
        except Exception:
            dow = dt.weekday()
        day = session_date_ist(bar.ts)
        prev_day = session_date_ist(bars[i - 1].ts) if i else None
        new_session = prev_day != day
        if dow == 0 and new_session:
            week_open = bar.open
            in_long = False
        if week_open is None:
            continue
        limit = week_open * (1.0 - dip)
        if not in_long and bar.low <= limit:
            leans[i] = "CE"
            in_long = True
            entry_px = limit
        elif in_long:
            if bar.high >= entry_px * (1.0 + target):
                leans[i] = "PE"
                in_long = False
            elif dow == 4 and (i + 1 >= len(bars) or session_date_ist(bars[i + 1].ts) != day):
                leans[i] = "PE"
                in_long = False
    return leans


def csv_replay(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-003: TV CSV report generator. No OHLC signal. Always flat unless csv_long=1 test hook."""
    if int(params.get("csv_long", 0)) == 1:
        n = len(bars)
        mid = max(1, n // 3)
        leans = ["HOLD"] * n
        leans[mid] = "CE"
        leans[min(n - 1, mid + 10)] = "PE"
        return leans
    return ["HOLD"] * len(bars)


def trendmaster_ma(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-004 tradeable core: short/long MA cross. FX session boxes skipped (NSE 09:15–15:30)."""
    kind = "sma"
    mt = params.get("ma_type_code", 0)
    if int(mt) == 1:
        kind = "ema"
    return _ma_cross_leans(
        bars,
        params,
        fast_key="Short_Term_MA_Length",
        slow_key="Long_Term_MA_Length",
        fast_default=9,
        slow_default=21,
        kind=kind,
    )


def double_tap(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-005: consecutive pivot highs/lows within tolerance → fade (double top/bottom)."""
    length = int(params.get("Pivot_Length", 50))
    tol = float(params.get("Pivot_Tolerance", 15.0))
    detect_bot = int(params.get("Detect_Bottoms", 1))
    detect_top = int(params.get("Detect_Tops", 1))
    n = len(bars)
    leans = ["HOLD"] * n
    if length < 3 or n < length + 2:
        return leans
    piv_hi: list[tuple[int, float]] = []
    piv_lo: list[tuple[int, float]] = []
    for i in range(length, n):
        window = bars[i - length + 1 : i + 1]
        hi = max(b.high for b in window)
        lo = min(b.low for b in window)
        if bars[i].high == hi and bars[i].high > bars[i - 1].high:
            piv_hi.append((i, bars[i].high))
        if bars[i].low == lo and bars[i].low < bars[i - 1].low:
            piv_lo.append((i, bars[i].low))
    def _tap(pivs: list[tuple[int, float]], fade: str) -> None:
        for j in range(1, len(pivs)):
            i0, p0 = pivs[j - 1]
            i1, p1 = pivs[j]
            if p0 == 0:
                continue
            if abs(p1 - p0) / p0 * 100.0 <= tol:
                leans[i1] = fade

    if detect_top:
        _tap(piv_hi, "PE")
    if detect_bot:
        _tap(piv_lo, "CE")
    return leans


def ema_trail(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-006: EMA fast/slow cross (trailing SL/target is simulator opposite, not TV trail engine)."""
    return _ma_cross_leans(
        bars,
        params,
        fast_key="Fast_len",
        slow_key="Slow_len",
        fast_default=20,
        slow_default=50,
        kind="ema",
    )


def tts_ma_cross(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-007 internal default: SMA 21/49 cross. Trailing template / 222 inputs not ported."""
    return _ma_cross_leans(
        bars,
        params,
        fast_key="fast",
        slow_key="slow",
        fast_default=21,
        slow_default=49,
        kind="sma",
    )


def bot3c_ma(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-008 3Commas bot default: EMA 21/50 cross. Alert webhook / 3Commas JSON omitted."""
    return _ma_cross_leans(
        bars,
        params,
        fast_key="MA_Length_1",
        slow_key="MA_Length_2",
        fast_default=21,
        slow_default=50,
        kind="ema",
    )


def pivot_rev(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-009 demo entries: pivot-high stop long / pivot-low stop short. Monthly table is viz."""
    left = int(params.get("leftBars", 2))
    right = int(params.get("rightBars", 1))
    n = len(bars)
    leans = ["HOLD"] * n
    span = left + right
    if n <= span + 1:
        return leans
    for i in range(span, n):
        mid = i - right
        if mid - left < 0:
            continue
        window = bars[mid - left : mid + right + 1]
        if bars[mid].high >= max(b.high for b in window) and all(
            bars[mid].high > bars[j].high for j in range(mid - left, mid) if j != mid
        ):
            leans[i] = "CE"
        elif bars[mid].low <= min(b.low for b in window):
            leans[i] = "PE"
    return leans


def stoch_kd(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-010: Stoch K/D cross (K<80 long, K>20 short). Leverage/margin is TV emulator only."""
    period_k = int(params.get("K", 13))
    period_d = int(params.get("D", 3))
    smooth = int(params.get("Smooth", 4))
    n = len(bars)
    raw: list[float | None] = [None] * n
    for i in range(n):
        if i + 1 < period_k:
            continue
        w = bars[i + 1 - period_k : i + 1]
        hh = max(b.high for b in w)
        ll = min(b.low for b in w)
        den = hh - ll
        raw[i] = 50.0 if den == 0 else 100.0 * (bars[i].close - ll) / den
    filled = [0.0 if x is None else x for x in raw]
    k = sma(filled, smooth)
    d = sma([0.0 if x is None else x for x in k], period_d)
    leans = ["HOLD"] * n
    for i in range(1, n):
        if _cross_up(k[i], d[i], k[i - 1], d[i - 1]) and (k[i] or 0) < 80:
            leans[i] = "CE"
        elif _cross_dn(k[i], d[i], k[i - 1], d[i - 1]) and (k[i] or 0) > 20:
            leans[i] = "PE"
    return leans


def risk_size_demo(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-011: hardcoded bar_index cadence (qty/risk is not a lean)."""
    every_l = int(params.get("long_every", 333))
    every_s = int(params.get("short_every", 444))
    leans = ["HOLD"] * len(bars)
    for i in range(len(bars)):
        if every_l and i % every_l == 0 and i:
            leans[i] = "CE"
        elif every_s and i % every_s == 0 and i:
            leans[i] = "PE"
    return leans


def osc_ma(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-012 default selector 'MA Crossover Strategy': EMA 3 vs Laguerre~WMA 9 proxy."""
    return _ma_cross_leans(
        bars,
        params,
        fast_key="MA_Crossover_Strat_Short_Length",
        slow_key="MA_Crossover_Strat_Long_Length",
        fast_default=3,
        slow_default=9,
        kind="ema",
    )


def keltner_stop(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-013: close cross of Keltner (EMA ± ATR*mult). Kelly sizing omitted."""
    length = int(params.get("length", 20))
    mult = float(params.get("Multiplier", 1.0))
    atr_len = int(params.get("ATR_Length", 10))
    closes = [b.close for b in bars]
    ma = ema(closes, length)
    atrs = _wilder_atr(bars, atr_len)
    leans = ["HOLD"] * len(bars)
    for i in range(1, len(bars)):
        if ma[i] is None or atrs[i] is None or ma[i - 1] is None or atrs[i - 1] is None:
            continue
        up = ma[i] + atrs[i] * mult  # type: ignore[operator]
        lo = ma[i] - atrs[i] * mult  # type: ignore[operator]
        up0 = ma[i - 1] + atrs[i - 1] * mult  # type: ignore[operator]
        lo0 = ma[i - 1] - atrs[i - 1] * mult  # type: ignore[operator]
        c, c0 = bars[i].close, bars[i - 1].close
        if c0 <= up0 and c > up:
            leans[i] = "CE"
        elif c0 >= lo0 and c < lo:
            leans[i] = "PE"
    return leans


def ext_signal_sma(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-014 template expects external ±1 source. Gap: close never ±1. SMA 14/28 stand-in."""
    return _ma_cross_leans(
        bars,
        params,
        fast_key="fast",
        slow_key="slow",
        fast_default=14,
        slow_default=28,
        kind="sma",
    )


def sma_sltp_money(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-015: SMA 14/28 entries. Dollar SL/TP needs tick value — gap, reversal only."""
    return _ma_cross_leans(bars, params, fast_default=14, slow_default=28, kind="sma")


def sma_step_trail(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-016: long-only SMA 14/28. Stepped trail not in lean simulator."""
    return _ma_cross_leans(bars, params, fast_default=14, slow_default=28, kind="sma", long_only=True)


def pmax(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-017 PMax: EMA(hl2) vs ATR trailing stop (default type EMA). Screener symbols omitted."""
    atr_len = int(params.get("ATR_Length", 10))
    mult = float(params.get("ATR_Multiplier", 3.0))
    ma_len = int(params.get("Moving_Average_Length", 10))
    src = [(b.high + b.low) / 2.0 for b in bars]
    mavg = ema(src, ma_len)
    atrs = _wilder_atr(bars, atr_len)
    n = len(bars)
    pmax_line: list[float | None] = [None] * n
    direction = 1
    long_stop = 0.0
    short_stop = 0.0
    for i in range(n):
        if mavg[i] is None or atrs[i] is None:
            continue
        ls = mavg[i] - mult * atrs[i]  # type: ignore[operator]
        ss = mavg[i] + mult * atrs[i]  # type: ignore[operator]
        if pmax_line[i - 1] is None if i else True:
            long_stop, short_stop = ls, ss
            direction = 1
            pmax_line[i] = long_stop
            continue
        long_stop = max(ls, long_stop) if mavg[i] > long_stop else ls
        short_stop = min(ss, short_stop) if mavg[i] < short_stop else ss
        if direction == -1 and mavg[i] > short_stop:
            direction = 1
        elif direction == 1 and mavg[i] < long_stop:
            direction = -1
        pmax_line[i] = long_stop if direction == 1 else short_stop
    leans = ["HOLD"] * n
    for i in range(1, n):
        if _cross_up(mavg[i], pmax_line[i], mavg[i - 1], pmax_line[i - 1]):
            leans[i] = "CE"
        elif _cross_dn(mavg[i], pmax_line[i], mavg[i - 1], pmax_line[i - 1]):
            leans[i] = "PE"
    return leans


def grid_like(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-018: baseline ± point grid. Martingale qty ignored (lean = direction only)."""
    point = float(params.get("point", 2.0))
    n = len(bars)
    leans = ["HOLD"] * n
    if not bars:
        return leans
    baseline = bars[0].close
    for i, bar in enumerate(bars):
        if bar.close > baseline + point:
            leans[i] = "CE"
            baseline = bar.close
        elif bar.close < baseline - point:
            leans[i] = "PE"
            baseline = bar.close
    return leans


def gap_fill(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-019: fade session opening gap (default invert=false)."""
    invert = int(params.get("invert", 0)) == 1
    leans = ["HOLD"] * len(bars)
    for i in range(1, len(bars)):
        if session_date_ist(bars[i].ts) == session_date_ist(bars[i - 1].ts):
            continue
        o, c = bars[i].open, bars[i].close
        p = bars[i - 1]
        upgap = o > p.high and min(c, o) > max(p.close, p.open)
        dngap = o < p.low and min(p.close, p.open) > max(c, o)
        if invert:
            if upgap:
                leans[i] = "CE"
            elif dngap:
                leans[i] = "PE"
        else:
            if dngap:
                leans[i] = "CE"
            elif upgap:
                leans[i] = "PE"
    return leans


def macd_martingale(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-020: first long when MACD fast>slow (AP=EMA2). Pyramid qty not in leans. Crypto martingale."""
    hist = macd_hist(
        [b.close for b in bars],
        fast=int(params.get("fast", 12)),
        slow=int(params.get("slow", 26)),
        signal=int(params.get("signal", 9)),
    )
    # Script uses Fast=EMA(EMA(close,2),12) vs Slow=EMA(EMA(close,2),26)
    ap = ema([b.close for b in bars], 2)
    ap_f = [0.0 if x is None else x for x in ap]
    fast = ema(ap_f, int(params.get("fast", 12)))
    slow = ema(ap_f, int(params.get("slow", 26)))
    tp = float(params.get("Take_Profit_Percent", 5.0)) / 100.0
    leans = ["HOLD"] * len(bars)
    in_long = False
    entry = 0.0
    for i in range(1, len(bars)):
        bull = fast[i] is not None and slow[i] is not None and fast[i] > slow[i]
        if bull and not in_long:
            leans[i] = "CE"
            in_long = True
            entry = bars[i].close
        elif in_long and bars[i].high >= entry * (1.0 + tp):
            leans[i] = "PE"
            in_long = False
        elif in_long and not bull:
            # stay; martingale on drop is qty not exit
            pass
        _ = hist
    return leans


def lube_friction(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-021: price-revisit 'friction' + 4-tap FIR trend. Crypto 30m origin."""
    barsback = int(params.get("bars_back", 50))  # TV default 500; tunable
    flevel = float(params.get("friction_stop", 50)) / 100.0
    tlevel = float(params.get("friction_start", -10)) / 100.0
    rng = int(params.get("lowest_friction_bars", 100))
    n = len(bars)
    friction = [0.0] * n
    closes = [b.close for b in bars]
    for i in range(n):
        acc = 0.0
        look = min(barsback, i)
        for j in range(1, look + 1):
            prev = bars[i - j]
            if prev.high >= closes[i] and prev.low <= closes[i]:
                acc += (1 + barsback) / (j + barsback)
        friction[i] = acc
    fir = [0.0] * n
    for i in range(n):
        s0 = closes[i]
        s1 = closes[i - 1] if i >= 1 else s0
        s2 = closes[i - 2] if i >= 2 else s1
        s3 = closes[i - 3] if i >= 3 else s2
        fir[i] = (4 * s0 + 3 * s1 + 2 * s2 + s3) / 10.0
    leans = ["HOLD"] * n
    for i in range(max(21, rng), n):
        w = friction[i + 1 - rng : i + 1]
        lowf, highf = min(w), max(w)
        midf = lowf * (1 - flevel) + highf * flevel
        lowf2 = lowf * (1 - tlevel) + highf * tlevel
        trend = 1 if fir[i] > fir[i - 1] else -1
        lag = friction[max(0, i - 5)]
        long_ = friction[i] < lowf2 and trend == 1
        short_ = friction[i] < lowf2 and trend == -1
        end = lag > midf
        if long_:
            leans[i] = "CE"
        elif short_:
            leans[i] = "PE"
        elif end:
            leans[i] = "HOLD"
    return leans


def timed_sma(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-022: SMA cross with date/session filters defaulted to always-on (0000-0000)."""
    return _ma_cross_leans(
        bars,
        params,
        fast_key="FastMA_Length",
        slow_key="SlowMA_Length",
        fast_default=14,
        slow_default=28,
        kind="sma",
        long_only=True,
    )


def grover_llorens(bars: list[Bar], params: dict[str, float]) -> list[str]:
    """EP-023: SAR-like activator. Default length=480 is slow on 1m; expose length."""
    length = int(params.get("length", 480))
    mult = float(params.get("mult", 14.0))
    n = len(bars)
    leans = ["HOLD"] * n
    atrs = _wilder_atr(bars, max(2, length))
    ts = 0.0
    prev_diff = 0.0
    val = 0.0
    bars_since = 0
    started = False
    for i, bar in enumerate(bars):
        src = bar.close
        if not started:
            ts = src
            started = True
            prev_diff = 0.0
            continue
        if atrs[i] is None:
            continue
        diff = src - ts
        atr = atrs[i]
        up = prev_diff <= 0 and diff > 0
        dn = prev_diff >= 0 and diff < 0
        if up or dn:
            val = atr / length  # type: ignore[operator]
            bars_since = 0
            if up:
                ts = ts - atr * mult  # type: ignore[operator]
                leans[i] = "CE"
            else:
                ts = ts + atr * mult  # type: ignore[operator]
                leans[i] = "PE"
        else:
            bars_since += 1
            sign = 1.0 if diff >= 0 else -1.0
            ts = ts + sign * val * bars_since
        prev_diff = diff
    return leans


PORT_FNS = {
    "ag_sell": ag_sell,
    "one_pct_week": one_pct_week,
    "csv_replay": csv_replay,
    "trendmaster_ma": trendmaster_ma,
    "double_tap": double_tap,
    "ema_trail": ema_trail,
    "tts_ma_cross": tts_ma_cross,
    "bot3c_ma": bot3c_ma,
    "pivot_rev": pivot_rev,
    "stoch_kd": stoch_kd,
    "risk_size_demo": risk_size_demo,
    "osc_ma": osc_ma,
    "keltner_stop": keltner_stop,
    "ext_signal_sma": ext_signal_sma,
    "sma_sltp_money": sma_sltp_money,
    "sma_step_trail": sma_step_trail,
    "pmax": pmax,
    "grid_like": grid_like,
    "gap_fill": gap_fill,
    "macd_martingale": macd_martingale,
    "lube_friction": lube_friction,
    "timed_sma": timed_sma,
    "grover_llorens": grover_llorens,
}
