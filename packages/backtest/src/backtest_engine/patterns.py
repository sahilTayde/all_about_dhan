"""WEB / PATTERN leans from INDEX OHLC. PROJECT_MIX folklore — not Dhan STRATs."""

from __future__ import annotations

import math
from collections import defaultdict

from backtest_engine.clocks import minutes_ist, session_date_ist
from backtest_engine.indicators import Bar, ema, session_vwap, sma, rsi


def _stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def _atr(bars: list[Bar], period: int = 14) -> list[float | None]:
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
    prev = first
    for i in range(period + 1, len(bars)):
        prev = (prev * (period - 1) + trs[i]) / period
        out[i] = prev
    return out


def _daily(bars: list[Bar]) -> dict[str, tuple[float, float, float]]:
    """session -> (high, low, close of last bar)."""
    bucket: dict[str, list[Bar]] = defaultdict(list)
    for bar in bars:
        bucket[session_date_ist(bar.ts)].append(bar)
    out: dict[str, tuple[float, float, float]] = {}
    for day, rows in bucket.items():
        out[day] = (max(b.high for b in rows), min(b.low for b in rows), rows[-1].close)
    return out


def _prev_day_map(daily: dict[str, tuple[float, float, float]]) -> dict[str, tuple[float, float, float]]:
    days = sorted(daily)
    prev: dict[str, tuple[float, float, float]] = {}
    for i, day in enumerate(days):
        if i == 0:
            continue
        prev[day] = daily[days[i - 1]]
    return prev


def lean_mom_body(bars: list[Bar]) -> list[str]:
    out = []
    for bar in bars:
        if bar.close > bar.open:
            out.append("CE")
        elif bar.close < bar.open:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_streak3(bars: list[Bar]) -> list[str]:
    bodies = lean_mom_body(bars)
    out = ["SKIP"] * len(bars)
    for i in range(2, len(bars)):
        chunk = bodies[i - 2 : i + 1]
        if chunk == ["CE", "CE", "CE"]:
            out[i] = "CE"
        elif chunk == ["PE", "PE", "PE"]:
            out[i] = "PE"
    return out


def lean_roc10(bars: list[Bar]) -> list[str]:
    out: list[str] = []
    for i, bar in enumerate(bars):
        if i < 10:
            out.append("SKIP")
            continue
        prev = bars[i - 10].close
        if prev <= 0:
            out.append("SKIP")
        elif bar.close > prev:
            out.append("CE")
        elif bar.close < prev:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_ema_cross(bars: list[Bar], fast: int, slow: int) -> list[str]:
    c = [b.close for b in bars]
    a, b = ema(c, fast), ema(c, slow)
    out = []
    for x, y in zip(a, b):
        if x is None or y is None:
            out.append("SKIP")
        elif x > y:
            out.append("CE")
        elif x < y:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_ema_20_50(bars: list[Bar]) -> list[str]:
    return lean_ema_cross(bars, 20, 50)


def lean_sma_cross(bars: list[Bar], fast: int, slow: int) -> list[str]:
    c = [b.close for b in bars]
    a, b = sma(c, fast), sma(c, slow)
    out = []
    for x, y in zip(a, b):
        if x is None or y is None:
            out.append("SKIP")
        elif x > y:
            out.append("CE")
        elif x < y:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_rsi_mr(bars: list[Bar], lo: float = 30.0, hi: float = 70.0) -> list[str]:
    """Annexure RSI_14 mean-reversion: oversold CE, overbought PE."""
    r = rsi([b.close for b in bars], 14)
    out = []
    for v in r:
        if v is None:
            out.append("SKIP")
        elif v <= lo:
            out.append("CE")
        elif v >= hi:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_rsi_trend(bars: list[Bar], mid: float = 50.0) -> list[str]:
    r = rsi([b.close for b in bars], 14)
    out = []
    for v in r:
        if v is None:
            out.append("SKIP")
        elif v > mid:
            out.append("CE")
        elif v < mid:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_donchian_n(bars: list[Bar], n: int = 20) -> list[str]:
    out = []
    for i, bar in enumerate(bars):
        if i < n:
            out.append("SKIP")
            continue
        window = bars[i - n : i]
        hi = max(b.high for b in window)
        lo = min(b.low for b in window)
        if bar.close > hi:
            out.append("CE")
        elif bar.close < lo:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_donchian20(bars: list[Bar]) -> list[str]:
    return lean_donchian_n(bars, 20)


def lean_bb_break(bars: list[Bar], length: int = 20, k: float = 2.0) -> list[str]:
    c = [b.close for b in bars]
    mid = sma(c, length)
    out = []
    for i, bar in enumerate(bars):
        m = mid[i]
        if m is None or i + 1 < length:
            out.append("SKIP")
            continue
        sd = _stdev(c[i + 1 - length : i + 1])
        up, dn = m + k * sd, m - k * sd
        if bar.close > up:
            out.append("CE")
        elif bar.close < dn:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_keltner(bars: list[Bar]) -> list[str]:
    c = [b.close for b in bars]
    mid = ema(c, 20)
    atrs = _atr(bars, 14)
    out = []
    for i, bar in enumerate(bars):
        m, a = mid[i], atrs[i]
        if m is None or a is None:
            out.append("SKIP")
            continue
        if bar.close > m + 1.5 * a:
            out.append("CE")
        elif bar.close < m - 1.5 * a:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_engulf(bars: list[Bar]) -> list[str]:
    out = ["SKIP"]
    for i in range(1, len(bars)):
        p, b = bars[i - 1], bars[i]
        bull = b.close > b.open and p.close < p.open and b.open <= p.close and b.close >= p.open
        bear = b.close < b.open and p.close > p.open and b.open >= p.close and b.close <= p.open
        if bull:
            out.append("CE")
        elif bear:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_inside_brk(bars: list[Bar]) -> list[str]:
    out = ["SKIP", "SKIP"]
    for i in range(2, len(bars)):
        a, b, c = bars[i - 2], bars[i - 1], bars[i]
        inside = b.high <= a.high and b.low >= a.low
        if not inside:
            out.append("SKIP")
            continue
        if c.close > a.high:
            out.append("CE")
        elif c.close < a.low:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_nr7_brk(bars: list[Bar]) -> list[str]:
    out: list[str] = []
    for i, bar in enumerate(bars):
        if i < 7:
            out.append("SKIP")
            continue
        ranges = [bars[j].high - bars[j].low for j in range(i - 6, i + 1)]
        if ranges[-1] != min(ranges):
            out.append("SKIP")
            continue
        hi = max(b.high for b in bars[i - 6 : i])
        lo = min(b.low for b in bars[i - 6 : i])
        if bar.close > hi:
            out.append("CE")
        elif bar.close < lo:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_sar(bars: list[Bar], af: float = 0.02, af_max: float = 0.2) -> list[str]:
    if len(bars) < 3:
        return ["SKIP"] * len(bars)
    out = ["SKIP", "SKIP"]
    long = bars[1].close >= bars[0].close
    ep = bars[1].high if long else bars[1].low
    sar = bars[0].low if long else bars[0].high
    accel = af
    for i in range(2, len(bars)):
        bar = bars[i]
        sar = sar + accel * (ep - sar)
        if long:
            if bar.low < sar:
                long = False
                sar = ep
                ep = bar.low
                accel = af
                out.append("PE")
            else:
                if bar.high > ep:
                    ep = bar.high
                    accel = min(af_max, accel + af)
                out.append("CE")
        else:
            if bar.high > sar:
                long = True
                sar = ep
                ep = bar.high
                accel = af
                out.append("CE")
            else:
                if bar.low < ep:
                    ep = bar.low
                    accel = min(af_max, accel + af)
                out.append("PE")
    return out


def lean_adx_di(bars: list[Bar], period: int = 14) -> list[str]:
    n = len(bars)
    out: list[str] = ["SKIP"] * n
    if n < period + 2:
        return out
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    tr = [0.0] * n
    for i in range(1, n):
        up = bars[i].high - bars[i - 1].high
        dn = bars[i - 1].low - bars[i].low
        plus_dm[i] = up if up > dn and up > 0 else 0.0
        minus_dm[i] = dn if dn > up and dn > 0 else 0.0
        tr[i] = max(
            bars[i].high - bars[i].low,
            abs(bars[i].high - bars[i - 1].close),
            abs(bars[i].low - bars[i - 1].close),
        )
    atr = sum(tr[1 : period + 1]) / period
    pdm = sum(plus_dm[1 : period + 1]) / period
    mdm = sum(minus_dm[1 : period + 1]) / period
    for i in range(period + 1, n):
        atr = (atr * (period - 1) + tr[i]) / period
        pdm = (pdm * (period - 1) + plus_dm[i]) / period
        mdm = (mdm * (period - 1) + minus_dm[i]) / period
        if atr <= 0:
            continue
        pdi = 100 * pdm / atr
        mdi = 100 * mdm / atr
        dx = 100 * abs(pdi - mdi) / (pdi + mdi) if (pdi + mdi) else 0.0
        if dx < 20:
            continue
        if pdi > mdi:
            out[i] = "CE"
        elif mdi > pdi:
            out[i] = "PE"
    return out


def lean_range_exp(bars: list[Bar]) -> list[str]:
    atrs = _atr(bars, 14)
    bodies = lean_mom_body(bars)
    out = []
    buf: list[float] = []
    for i, a in enumerate(atrs):
        if a is None:
            out.append("SKIP")
            continue
        buf.append(a)
        if len(buf) < 14:
            out.append("SKIP")
            continue
        avg = sum(buf[-14:]) / 14
        if a > 1.2 * avg:
            out.append(bodies[i])
        else:
            out.append("SKIP")
    return out


def lean_pdh_pdl(bars: list[Bar]) -> list[str]:
    daily = _daily(bars)
    prev = _prev_day_map(daily)
    out = []
    for bar in bars:
        day = session_date_ist(bar.ts)
        p = prev.get(day)
        if not p:
            out.append("SKIP")
            continue
        hi, lo, _c = p
        if bar.close > hi:
            out.append("CE")
        elif bar.close < lo:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_gap(bars: list[Bar]) -> list[str]:
    daily = _daily(bars)
    prev = _prev_day_map(daily)
    first: dict[str, Bar] = {}
    for bar in bars:
        d = session_date_ist(bar.ts)
        if d not in first:
            first[d] = bar
    out = []
    for bar in bars:
        d = session_date_ist(bar.ts)
        p = prev.get(d)
        if not p or first.get(d) is not bar:
            out.append("SKIP")
            continue
        _h, _l, pc = p
        if bar.open > pc:
            out.append("CE")
        elif bar.open < pc:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_cpr_bias(bars: list[Bar]) -> list[str]:
    daily = _daily(bars)
    prev = _prev_day_map(daily)
    out = []
    for bar in bars:
        p = prev.get(session_date_ist(bar.ts))
        if not p:
            out.append("SKIP")
            continue
        h, l, c = p
        pivot = (h + l + c) / 3.0
        bc = (h + l) / 2.0
        tc = 2.0 * pivot - bc
        if bar.close > tc:
            out.append("CE")
        elif bar.close < bc:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_pivot_r1(bars: list[Bar]) -> list[str]:
    daily = _daily(bars)
    prev = _prev_day_map(daily)
    out = []
    for bar in bars:
        p = prev.get(session_date_ist(bar.ts))
        if not p:
            out.append("SKIP")
            continue
        h, l, c = p
        pivot = (h + l + c) / 3.0
        r1 = 2 * pivot - l
        s1 = 2 * pivot - h
        if bar.close > r1:
            out.append("CE")
        elif bar.close < s1:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_orb_15(bars_1m: list[Bar], bars_3m: list[Bar]) -> list[str]:
    """9:15–9:30 IST range from 1m; 3m close beyond range after 9:30."""
    by_day: dict[str, list[Bar]] = defaultdict(list)
    for bar in bars_1m:
        by_day[session_date_ist(bar.ts)].append(bar)
    orb: dict[str, tuple[float, float]] = {}
    for day, rows in by_day.items():
        window = [b for b in rows if 9 * 60 + 15 <= minutes_ist(b.ts) < 9 * 60 + 30]
        if not window:
            continue
        orb[day] = (max(b.high for b in window), min(b.low for b in window))
    out = []
    for bar in bars_3m:
        day = session_date_ist(bar.ts)
        rng = orb.get(day)
        if not rng or minutes_ist(bar.ts) < 9 * 60 + 30:
            out.append("SKIP")
            continue
        hi, lo = rng
        if bar.close > hi:
            out.append("CE")
        elif bar.close < lo:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_orb_vwap(bars_1m: list[Bar], bars_3m: list[Bar]) -> list[str]:
    orb = lean_orb_15(bars_1m, bars_3m)
    vw = session_vwap(bars_3m, equal_weight_if_no_volume=True)
    out = []
    for i, bar in enumerate(bars_3m):
        side = orb[i]
        v = vw[i]
        if side not in ("CE", "PE") or v is None:
            out.append("SKIP")
        elif side == "CE" and bar.close > v:
            out.append("CE")
        elif side == "PE" and bar.close < v:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def lean_cpr_orb(bars_1m: list[Bar], bars_3m: list[Bar]) -> list[str]:
    orb = lean_orb_15(bars_1m, bars_3m)
    cpr = lean_cpr_bias(bars_3m)
    out = []
    for a, b in zip(orb, cpr):
        if a in ("CE", "PE") and a == b:
            out.append(a)
        else:
            out.append("SKIP")
    return out


def catalog_leans(bars_1m: list[Bar], bars_3m: list[Bar]) -> dict[str, tuple[list[str], bool]]:
    """mix_id -> (leans on 3m, skip_open_entries). skip_open False for ORB books."""
    return {
        "MIX-MOM-BODY": (lean_mom_body(bars_3m), True),
        "MIX-STREAK-3": (lean_streak3(bars_3m), True),
        "MIX-ROC-10": (lean_roc10(bars_3m), True),
        "MIX-EMA-20-50": (lean_ema_20_50(bars_3m), True),
        "MIX-DONCHIAN-20": (lean_donchian20(bars_3m), True),
        "MIX-BB-BREAK": (lean_bb_break(bars_3m), True),
        "MIX-KELTNER": (lean_keltner(bars_3m), True),
        "MIX-ENGULF": (lean_engulf(bars_3m), True),
        "MIX-INSIDE-BRK": (lean_inside_brk(bars_3m), True),
        "MIX-NR7-BRK": (lean_nr7_brk(bars_3m), True),
        "MIX-SAR": (lean_sar(bars_3m), True),
        "MIX-ADX-DI": (lean_adx_di(bars_3m), True),
        "MIX-RANGE-EXP": (lean_range_exp(bars_3m), True),
        "MIX-PDH-PDL": (lean_pdh_pdl(bars_3m), True),
        "MIX-GAP": (lean_gap(bars_3m), False),
        "MIX-CPR-BIAS": (lean_cpr_bias(bars_3m), True),
        "MIX-PIVOT-R1": (lean_pivot_r1(bars_3m), True),
        "MIX-ORB-15": (lean_orb_15(bars_1m, bars_3m), False),
        "MIX-ORB-VWAP": (lean_orb_vwap(bars_1m, bars_3m), False),
        "MIX-CPR-ORB": (lean_cpr_orb(bars_1m, bars_3m), False),
    }
