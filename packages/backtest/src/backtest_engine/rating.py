"""Honest OOS ratings. Proxy points ≠ option P/L. Never a promote by itself."""

from __future__ import annotations

from typing import Iterable

from backtest_engine.simulate import Trade

MIN_OOS_TRADES = 30
MIN_IS_TRADES = 30
OOS_FRACTION = 0.20


def split_ts(trades: list[Trade]) -> int | None:
    if not trades:
        return None
    times = sorted(t.entry_ts for t in trades)
    cut = times[max(0, int(len(times) * (1.0 - OOS_FRACTION)) - 1)]
    return cut


def _stats(trades: Iterable[Trade]) -> dict:
    rows = list(trades)
    n = len(rows)
    if n == 0:
        return {
            "n": 0,
            "wins": 0,
            "win_rate": None,
            "expectancy_pts": None,
            "sum_pts": None,
            "profit_factor": None,
            "max_dd_pts": None,
        }
    pts = [t.points for t in rows]
    wins = sum(1 for p in pts if p > 0)
    win_sum = sum(p for p in pts if p > 0)
    loss_sum = abs(sum(p for p in pts if p < 0))
    pf = round(win_sum / loss_sum, 4) if loss_sum else None
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pts:
        equity += p
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    return {
        "n": n,
        "wins": wins,
        "win_rate": round(wins / n, 4),
        "expectancy_pts": round(sum(pts) / n, 4),
        "sum_pts": round(sum(pts), 4),
        "profit_factor": pf,
        "max_dd_pts": round(max_dd, 4),
    }


def rate_trades(trades: list[Trade], *, book_id: str) -> dict:
    """Letter is HYPOTHESIS. validated=false until 09 five-pass + option fills."""
    if not trades:
        return {
            "book_id": book_id,
            "rating": "DATA_INSUFFICIENT",
            "validated": False,
            "promote": False,
            "reason": "zero trades",
            "pnl_unit": "UNDERLYING_POINTS_PROXY",
            "option_pnl": None,
            "is": _stats([]),
            "oos": _stats([]),
            "all": _stats([]),
        }
    cut = split_ts(trades)
    assert cut is not None
    is_rows = [t for t in trades if t.entry_ts <= cut]
    oos_rows = [t for t in trades if t.entry_ts > cut]
    return _letters(is_rows, oos_rows, trades, book_id)


def rate_split(is_rows: list[Trade], oos_rows: list[Trade], *, book_id: str) -> dict:
    """Use a frozen IS/OOS cut (nested grid). Same letter rules as rate_trades."""
    return _letters(is_rows, oos_rows, is_rows + oos_rows, book_id)


def _letters(
    is_rows: list[Trade], oos_rows: list[Trade], all_rows: list[Trade], book_id: str
) -> dict:
    is_s = _stats(is_rows)
    oos_s = _stats(oos_rows)
    all_s = _stats(all_rows)
    n_oos = oos_s["n"]
    n_is = is_s["n"]
    rating = "DATA_INSUFFICIENT"
    reason = f"need {MIN_OOS_TRADES} OOS trades (have {n_oos}); IS min {MIN_IS_TRADES} (have {n_is})"
    if n_oos >= MIN_OOS_TRADES and n_is >= MIN_IS_TRADES:
        wr = oos_s["win_rate"] or 0.0
        exp = oos_s["expectancy_pts"] or 0.0
        if exp <= 0:
            rating = "FAIL"
            reason = "OOS expectancy_pts <= 0 after proxy fills (not option costs)"
        elif wr >= 0.55 and exp > 0:
            rating = "CANDIDATE"
            reason = "OOS proxy expectancy > 0 and win_rate >= 55%. Still UNVALIDATED. Not a promote."
        elif wr >= 0.45:
            rating = "WEAK"
            reason = "OOS proxy mixed. Keep in BACKTEST_BOOK. Not a promote."
        else:
            rating = "FAIL"
            reason = "OOS proxy win_rate < 45%."
    return {
        "book_id": book_id,
        "rating": rating,
        "validated": False,
        "promote": False,
        "keep_current_strategy": True,
        "reason": reason,
        "pnl_unit": "UNDERLYING_POINTS_PROXY",
        "option_pnl": None,
        "session_kind": "UNKNOWN",
        "news_filter": "DATA_INSUFFICIENT",
        "is": is_s,
        "oos": oos_s,
        "all": all_s,
        "min_oos_trades": MIN_OOS_TRADES,
    }
