"""Paper algos for STRAT-003 / 001 / 006 + filters 007 / 008 / 009. No orders."""

from __future__ import annotations

from typing import Optional

from backtest_engine.clocks import allow_007
from backtest_engine.indicators import Bar, all_three, ema, macd_hist, sma
from backtest_engine.resample import resample
from backtest_engine.simulate import Trade, simulate_leans


def strat_003_leans(bars: list[Bar], *, equal_weight_vwap: bool = False) -> list[str]:
    return all_three(bars, equal_weight_vwap=equal_weight_vwap)


def run_strat_003(
    bars: list[Bar],
    *,
    underlying: str,
    use_007: bool = True,
    use_009: bool = True,
    veto_sessions: Optional[set[str]] = None,
    equal_weight_vwap: bool = False,
    strategy_id: str = "STRAT-003",
) -> list[Trade]:
    leans = strat_003_leans(bars, equal_weight_vwap=equal_weight_vwap)
    allow = [allow_007(b.ts) if use_007 else True for b in bars]
    return simulate_leans(
        bars,
        leans,
        strategy_id=strategy_id,
        underlying=underlying,
        use_009=use_009,
        veto_sessions=veto_sessions,
        allow_entry=allow,
    )


def _align_parent_child(parent: list[Bar], child: list[Bar]) -> list[int]:
    """For each child bar, index of last parent bar with ts <= child.ts."""
    j = 0
    out: list[int] = []
    for bar in child:
        while j + 1 < len(parent) and parent[j + 1].ts <= bar.ts:
            j += 1
        out.append(j)
    return out


def strat_001_child(bars_1m: list[Bar]) -> tuple[list[Bar], list[str]]:
    """Parent 60m + child 5m MACD hist and SMA 10>30>100. PROJECT_MIX on index."""
    parent = resample(bars_1m, 60)
    child = resample(bars_1m, 5)
    if not parent or not child:
        return [], []
    p_close = [b.close for b in parent]
    c_close = [b.close for b in child]
    p_hist = macd_hist(p_close)
    c_hist = macd_hist(c_close)
    p10, p30, p100 = sma(p_close, 10), sma(p_close, 30), sma(p_close, 100)
    c10, c30, c100 = sma(c_close, 10), sma(c_close, 30), sma(c_close, 100)
    idx = _align_parent_child(parent, child)
    leans: list[str] = []
    for i, _bar in enumerate(child):
        pi = idx[i]
        vals = (
            p_hist[pi],
            c_hist[i],
            p10[pi],
            p30[pi],
            p100[pi],
            c10[i],
            c30[i],
            c100[i],
        )
        if any(v is None for v in vals):
            leans.append("SKIP")
            continue
        ph, ch, a, b, c, d, e, f = vals
        bull = ph > 0 and ch > 0 and a > b > c and d > e > f
        bear = ph < 0 and ch < 0 and a < b < c and d < e < f
        if bull:
            leans.append("CE")
        elif bear:
            leans.append("PE")
        else:
            leans.append("SKIP")
    return child, leans


def strat_001_parent_leans(bars_1m: list[Bar]) -> tuple[list[Bar], list[str]]:
    """001 1h parent only: MACD hist + SMA 10/30/100. Not HAUS child buy-the-high."""
    parent = resample(bars_1m, 60)
    if not parent:
        return [], []
    p_close = [b.close for b in parent]
    p_hist = macd_hist(p_close)
    p10, p30, p100 = sma(p_close, 10), sma(p_close, 30), sma(p_close, 100)
    leans: list[str] = []
    for i in range(len(parent)):
        vals = (p_hist[i], p10[i], p30[i], p100[i])
        if any(v is None for v in vals):
            leans.append("SKIP")
            continue
        ph, a, b, c = vals
        if ph > 0 and a > b > c:
            leans.append("CE")
        elif ph < 0 and a < b < c:
            leans.append("PE")
        else:
            leans.append("SKIP")
    return parent, leans


def macd_hist_side(bars: list[Bar]) -> list[str]:
    """Appel 12/26/9 histogram sign. Confirm-or-kill only — not an entry recipe."""
    hist = macd_hist([b.close for b in bars])
    out: list[str] = []
    for v in hist:
        if v is None:
            out.append("SKIP")
        elif v > 0:
            out.append("CE")
        elif v < 0:
            out.append("PE")
        else:
            out.append("SKIP")
    return out


def align_leans_to(
    target: list[Bar], source: list[Bar], source_leans: list[str]
) -> list[str]:
    """Last source lean with ts <= target.ts (source bar already closed)."""
    j = 0
    n = min(len(source), len(source_leans))
    out: list[str] = []
    for bar in target:
        while j + 1 < n and source[j + 1].ts <= bar.ts:
            j += 1
        if n == 0 or source[j].ts > bar.ts:
            out.append("SKIP")
        else:
            out.append(source_leans[j])
    return out


def and_same_side(primary: list[str], gate: list[str]) -> list[str]:
    n = min(len(primary), len(gate))
    out: list[str] = []
    for i in range(n):
        a, b = primary[i], gate[i]
        if a in ("CE", "PE") and a == b:
            out.append(a)
        else:
            out.append("SKIP")
    return out


def and_many(leans: list[list[str]]) -> list[str]:
    if not leans:
        return []
    n = min(len(x) for x in leans)
    acc = leans[0][:n]
    for other in leans[1:]:
        acc = and_same_side(acc, other[:n])
    return acc


def run_strat_001(
    bars_1m: list[Bar],
    *,
    underlying: str,
    use_007: bool = True,
    use_009: bool = True,
    veto_sessions: Optional[set[str]] = None,
) -> list[Trade]:
    child, leans = strat_001_child(bars_1m)
    if not child:
        return []
    allow = [allow_007(b.ts) if use_007 else True for b in child]
    return simulate_leans(
        child,
        leans,
        strategy_id="STRAT-001",
        underlying=underlying,
        use_009=use_009,
        veto_sessions=veto_sessions,
        allow_entry=allow,
    )


def strat_006_leans(bars_1m: list[Bar]) -> tuple[list[Bar], list[str]]:
    """Spoken 2m EMA 10/20. HQ has no 2m — resample from 1m. VIX filter DATA_INSUFFICIENT."""
    bars = resample(bars_1m, 2)
    closes = [b.close for b in bars]
    e10 = ema(closes, 10)
    e20 = ema(closes, 20)
    leans: list[str] = []
    for i, _bar in enumerate(bars):
        a, b = e10[i], e20[i]
        if a is None or b is None:
            leans.append("SKIP")
        elif a > b:
            leans.append("CE")
        elif a < b:
            leans.append("PE")
        else:
            leans.append("SKIP")
    return bars, leans


def run_strat_006(
    bars_1m: list[Bar],
    *,
    underlying: str,
    use_009: bool = True,
    veto_sessions: Optional[set[str]] = None,
) -> list[Trade]:
    """Spoken 2m EMA 10/20. HQ has no 2m — resample from 1m. VIX filter DATA_INSUFFICIENT."""
    bars, leans = strat_006_leans(bars_1m)
    if not bars:
        return []
    return simulate_leans(
        bars,
        leans,
        strategy_id="STRAT-006",
        underlying=underlying,
        use_009=use_009,
        veto_sessions=veto_sessions,
    )


def daily_lean_at_open(bars: list[Bar], leans: list[str]) -> dict[str, str]:
    """First non-SKIP lean after 09:45 per session — for STRAT-008 alignment."""
    from backtest_engine.clocks import session_date_ist, skip_open_009

    out: dict[str, str] = {}
    for bar, lean in zip(bars, leans):
        if skip_open_009(bar.ts):
            continue
        if lean not in ("CE", "PE"):
            continue
        day = session_date_ist(bar.ts)
        if day not in out:
            out[day] = lean
    return out


def mixed_index_veto(daily_by_und: dict[str, dict[str, str]]) -> set[str]:
    """STRAT-008: if any pair of {NIFTY, BANKNIFTY, SENSEX} disagrees that day, veto."""
    days: set[str] = set()
    for table in daily_by_und.values():
        days.update(table.keys())
    veto: set[str] = set()
    names = [n for n in ("NIFTY", "BANKNIFTY", "SENSEX") if n in daily_by_und]
    for day in days:
        leans = [daily_by_und[n].get(day) for n in names]
        present = [x for x in leans if x in ("CE", "PE")]
        if len(set(present)) > 1:
            veto.add(day)
    return veto
