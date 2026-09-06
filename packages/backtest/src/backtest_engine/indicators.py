"""OHLC compute for STRAT-003-style stack. Not a Dhan Supertrend REST field.

TV-style ATR(10)×3 close-flip is VALIDATION inference (02). HQ has no Supertrend series.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Bar:
    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float


def bars_from_chart(payload: dict) -> list[Bar]:
    opens = payload.get("open") or []
    highs = payload.get("high") or []
    lows = payload.get("low") or []
    closes = payload.get("close") or []
    vols = payload.get("volume") or []
    ts = payload.get("timestamp") or []
    n = min(len(opens), len(highs), len(lows), len(closes), len(vols), len(ts))
    out: list[Bar] = []
    for i in range(n):
        out.append(
            Bar(
                ts=int(ts[i]),
                open=float(opens[i]),
                high=float(highs[i]),
                low=float(lows[i]),
                close=float(closes[i]),
                volume=float(vols[i] or 0),
            )
        )
    return out


def session_vwap(bars: list[Bar], *, equal_weight_if_no_volume: bool = False) -> list[float | None]:
    """Cumulative typical-price VWAP. Resets when calendar day (UTC date of ts) changes.

    IST session split is applied by the caller via clocks. INDEX volume is UNKNOWN
    as a VWAP tape — equal-weight fallback is a PROJECT ablation, not FUTIDX.
    """
    out: list[float | None] = []
    num = 0.0
    den = 0.0
    last_day = None
    for bar in bars:
        day = bar.ts // 86400
        if last_day is not None and day != last_day:
            num = 0.0
            den = 0.0
        last_day = day
        typical = (bar.high + bar.low + bar.close) / 3.0
        weight = bar.volume if bar.volume > 0 else (1.0 if equal_weight_if_no_volume else 0.0)
        num += typical * weight
        den += weight
        out.append((num / den) if den else None)
    return out


def vwma(bars: list[Bar], length: int = 20, *, equal_weight: bool = False) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(bars)):
        window = bars[max(0, i + 1 - length) : i + 1]
        if len(window) < length:
            out.append(None)
            continue
        weights = [
            (b.volume if b.volume > 0 else (1.0 if equal_weight else 0.0)) for b in window
        ]
        num = sum(b.close * w for b, w in zip(window, weights))
        den = sum(weights)
        out.append((num / den) if den else None)
    return out


def _wilder_atr(bars: list[Bar], period: int) -> list[float | None]:
    atr: list[float | None] = [None] * len(bars)
    if len(bars) < period + 1:
        return atr
    trs: list[float] = []
    for i, bar in enumerate(bars):
        if i == 0:
            trs.append(bar.high - bar.low)
        else:
            prev = bars[i - 1].close
            trs.append(max(bar.high - bar.low, abs(bar.high - prev), abs(bar.low - prev)))
    first = sum(trs[1 : period + 1]) / period
    atr[period] = first
    prev_atr = first
    for i in range(period + 1, len(bars)):
        prev_atr = (prev_atr * (period - 1) + trs[i]) / period
        atr[i] = prev_atr
    return atr


def supertrend(bars: list[Bar], period: int = 10, mult: float = 3.0) -> list[float | None]:
    """Close-flip Supertrend. Inference — not an HQ field. Do not claim Dhan chart identity."""
    atrs = _wilder_atr(bars, period)
    st: list[float | None] = [None] * len(bars)
    direction = 1
    for i, bar in enumerate(bars):
        atr = atrs[i]
        if atr is None:
            continue
        hl2 = (bar.high + bar.low) / 2.0
        upper = hl2 + mult * atr
        lower = hl2 - mult * atr
        if i == 0 or st[i - 1] is None:
            st[i] = lower
            direction = 1
            continue
        prev = st[i - 1]
        assert prev is not None
        if direction == 1:
            st[i] = max(lower, prev) if bar.close > prev else upper
            if bar.close < st[i]:
                direction = -1
                st[i] = upper
        else:
            st[i] = min(upper, prev) if bar.close < prev else lower
            if bar.close > st[i]:
                direction = 1
                st[i] = lower
    return st


def all_three(bars: list[Bar], *, equal_weight_vwap: bool = False) -> list[str]:
    """CE if close > VWAP and VWMA20 and ST; PE if close < all three; else SKIP."""
    vw = session_vwap(bars, equal_weight_if_no_volume=equal_weight_vwap)
    vm = vwma(bars, 20, equal_weight=equal_weight_vwap)
    st = supertrend(bars, 10, 3.0)
    out: list[str] = []
    for i, bar in enumerate(bars):
        a, b, c = vw[i], vm[i], st[i]
        if a is None or b is None or c is None:
            out.append("SKIP")
            continue
        if bar.close > a and bar.close > b and bar.close > c:
            out.append("CE")
        elif bar.close < a and bar.close < b and bar.close < c:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def ema(values: list[float], length: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if length <= 0 or len(values) < length:
        return out
    k = 2.0 / (length + 1)
    seed = sum(values[:length]) / length
    out[length - 1] = seed
    prev = seed
    for i in range(length, len(values)):
        prev = values[i] * k + prev * (1.0 - k)
        out[i] = prev
    return out


def sma(values: list[float], length: int) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < length:
            out.append(None)
            continue
        window = values[i + 1 - length : i + 1]
        out.append(sum(window) / length)
    return out


def rsi(closes: list[float], period: int = 14) -> list[float | None]:
    """Wilder RSI. Annexure token RSI_14 — not a HQ series endpoint."""
    n = len(closes)
    out: list[float | None] = [None] * n
    if n < period + 1:
        return out
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    avg_g = gains / period
    avg_l = losses / period
    if avg_l == 0:
        out[period] = 100.0
    else:
        out[period] = 100.0 - 100.0 / (1.0 + avg_g / avg_l)
    for i in range(period + 1, n):
        d = closes[i] - closes[i - 1]
        g = d if d > 0 else 0.0
        l = -d if d < 0 else 0.0
        avg_g = (avg_g * (period - 1) + g) / period
        avg_l = (avg_l * (period - 1) + l) / period
        if avg_l == 0:
            out[i] = 100.0
        else:
            out[i] = 100.0 - 100.0 / (1.0 + avg_g / avg_l)
    return out


def macd_hist(
    closes: list[float],
    *,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> list[float | None]:
    """Appel 12/26/9 histogram. HAUS ×3/×4 stays a grid — this is the VALIDATION default."""
    fast_e = ema(closes, fast)
    slow_e = ema(closes, slow)
    macd_line: list[float | None] = []
    for a, b in zip(fast_e, slow_e):
        if a is None or b is None:
            macd_line.append(None)
        else:
            macd_line.append(a - b)
    filled = [0.0 if x is None else x for x in macd_line]
    sig = ema(filled, signal)
    out: list[float | None] = []
    for i, line in enumerate(macd_line):
        if line is None or sig[i] is None:
            out.append(None)
        else:
            out.append(line - sig[i])
    return out
