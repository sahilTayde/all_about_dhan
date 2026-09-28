"""Label sessions from data already known at that day. No future sessions."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

from exitlab.clock import as_ist
from exitlab.types import Bar, SessionLabel


def nifty_weekly_expiry(day: date) -> date:
    """NIFTY weekly expiry is Tuesday. Same-week Tuesday on or after `day` if Tue, else next."""
    # weekday(): Mon=0 ... Sun=6. Tuesday = 1.
    offset = (1 - day.weekday()) % 7
    return day + timedelta(days=offset)


def kaufman_er(closes: list[float], lookback: int = 15) -> float | None:
    if len(closes) < 2:
        return None
    window = closes[-lookback:] if lookback > 0 else closes
    if len(window) < 2:
        return None
    net = abs(window[-1] - window[0])
    path = sum(abs(window[i] - window[i - 1]) for i in range(1, len(window)))
    if path <= 1e-12:
        return 0.0
    return net / path


def atr(bars: list[Bar], n: int = 14) -> float | None:
    if len(bars) < 2:
        return None
    trs: list[float] = []
    prev = bars[0].close
    for bar in bars[1:]:
        tr = max(bar.high - bar.low, abs(bar.high - prev), abs(bar.low - prev))
        trs.append(tr)
        prev = bar.close
    if not trs:
        return None
    use = trs[-n:]
    return sum(use) / len(use)


def label_session(
    session: str,
    index_bars: list[Bar],
    *,
    prev_close: float | None,
    atm_iv: float | None,
    feed_freeze: bool,
    data_source: str,
    iv_median: float | None = None,
) -> SessionLabel:
    day = date.fromisoformat(session)
    wd = day.strftime("%A")
    expiry = nifty_weekly_expiry(day)
    expiry_day = day == expiry
    day_before = day == expiry - timedelta(days=1)
    if not index_bars:
        return SessionLabel(
            session=session,
            weekday=wd,
            expiry_day=expiry_day,
            day_before_expiry=day_before,
            scenario="DATA_INSUFFICIENT",
            tags=("DATA_INSUFFICIENT",),
            index_open=None,
            index_close=None,
            range_pts=None,
            atr=None,
            gap_pct=None,
            atm_iv=atm_iv,
            er=None,
            feed_freeze=feed_freeze,
            data_source=data_source,
            notes="no index bars in session window",
        )
    opens = index_bars[0].open
    close = index_bars[-1].close
    hi = max(b.high for b in index_bars)
    lo = min(b.low for b in index_bars)
    rng = hi - lo
    er = kaufman_er([b.close for b in index_bars], 30)
    atr14 = atr(index_bars, 14)
    gap_pct = None
    if prev_close and prev_close > 0:
        gap_pct = (opens - prev_close) / prev_close * 100.0
    tags: list[str] = []
    if expiry_day:
        tags.append("expiry")
    if day_before:
        tags.append("day_before_expiry")
    if gap_pct is not None and abs(gap_pct) >= 0.40:
        tags.append("gap_open")
    if feed_freeze:
        tags.append("feed_freeze")
    if atm_iv is not None and iv_median is not None:
        if atm_iv >= iv_median * 1.25:
            tags.append("high_iv")
        elif atm_iv <= iv_median * 0.80:
            tags.append("low_iv")
    move = close - opens
    trendish = er is not None and er >= 0.35 and abs(move) >= 40
    choppy = er is not None and er < 0.22
    if trendish and move > 0:
        tags.append("trend_up")
        scenario = "trend_up"
    elif trendish and move < 0:
        tags.append("trend_down")
        scenario = "trend_down"
    elif choppy:
        tags.append("chop")
        scenario = "chop"
    else:
        tags.append("mixed")
        scenario = "mixed"
    if expiry_day:
        scenario = f"expiry_{scenario}"
    return SessionLabel(
        session=session,
        weekday=wd,
        expiry_day=expiry_day,
        day_before_expiry=day_before,
        scenario=scenario,
        tags=tuple(tags),
        index_open=opens,
        index_close=close,
        range_pts=rng,
        atr=atr14,
        gap_pct=gap_pct,
        atm_iv=atm_iv,
        er=er,
        feed_freeze=feed_freeze,
        data_source=data_source,
    )


def prior_close(index_by_day: dict[str, list[Bar]], session: str) -> float | None:
    days = sorted(index_by_day)
    if session not in days:
        return None
    i = days.index(session)
    if i == 0:
        return None
    prev = index_by_day[days[i - 1]]
    if not prev:
        return None
    return prev[-1].close


def group_index_by_session(bars: Iterable[Bar]) -> dict[str, list[Bar]]:
    out: dict[str, list[Bar]] = {}
    for bar in bars:
        day = as_ist(bar.ts).date().isoformat()
        out.setdefault(day, []).append(bar)
    for day in out:
        out[day].sort(key=lambda b: b.available_ts)
    return out


def is_weekend(session: str) -> bool:
    return date.fromisoformat(session).weekday() >= 5
