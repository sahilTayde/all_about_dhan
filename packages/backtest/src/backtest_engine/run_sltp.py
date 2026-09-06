"""NIFTY SL/TP overlay backtest — named MIX exits on INDEX proxy.

Uses cached OHLC when present. No promote. No live orders.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.algos import strat_003_leans
from backtest_engine.clocks import allow_007
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.indicators import supertrend
from backtest_engine.rating import rate_trades
from backtest_engine.resample import resample
from backtest_engine.simulate_sltp import simulate_leans_sltp, simulate_st_flip_exit

IST = timezone(timedelta(hours=5, minutes=30))
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}


def _log(msg: str) -> None:
    print(f"[sltp] {msg}", file=sys.stderr, flush=True)


def _reason_breakdown(trades) -> dict[str, int]:
    return dict(Counter(t.reason for t in trades))


def run_sltp(
    client: DhanClient,
    *,
    years: float = 2.0,
    interval: int = 1,
    underlying: str = "NIFTY",
) -> dict[str, Any]:
    _, sid, seg, inst = INDEX_BY_NAME[underlying]
    _log(f"fetch {underlying} years={years} interval={interval}")
    series = fetch_range(
        client,
        security_id=sid,
        exchange_segment=seg,
        instrument=inst,
        interval=interval,
        years=years,
    )
    bars_1m = series.get("bars") or []

    bars_3m = resample(bars_1m, 3)
    _log(f"bars_1m={len(bars_1m)} bars_3m={len(bars_3m)}")
    leans = strat_003_leans(bars_3m, equal_weight_vwap=True)
    allow = [allow_007(b.ts) for b in bars_3m]

    books: list[dict] = []

    # MIX-DESK-IQ-ATR-RR2 / MIX-SLTP-ATR-R2
    for mult in (1.5, 2.0):
        book_id = f"MIX-DESK-IQ-ATR-RR2/NIFTY/ATR14x{mult}/R2"
        trades = simulate_leans_sltp(
            bars_3m,
            leans,
            strategy_id=book_id,
            underlying=underlying,
            method_id="MIX-DESK-IQ-ATR-RR2",
            atr_period=14,
            atr_mult=mult,
            rr=2.0,
            use_009=True,
            allow_entry=allow,
        )
        rating = rate_trades(trades, book_id=book_id)
        rating.update(
            {
                "mix_id": "MIX-DESK-IQ-ATR-RR2",
                "levels_method": "MIX-SLTP-ATR-R2",
                "atr_mult": mult,
                "rr": 2.0,
                "entry": "STRAT-003_all_three_INDEX_3m_proxy",
                "exit": "ATR_stop_or_R2_target_or_stack_or_flatten",
                "pnl_unit": "UNDERLYING_POINTS_PROXY",
                "promote": False,
                "validated": False,
                "keep_current_strategy": True,
                "reason_breakdown": _reason_breakdown(trades),
                "costs": "NONE_ON_INDEX_PROXY",
                "honesty": (
                    "INDEX 3m equal-weight VWAP proxy — not FUTIDX. "
                    "GEX filter not applied (DATA_INSUFFICIENT). Not a promote."
                ),
            }
        )
        if rating.get("rating") == "CANDIDATE":
            rating["rating"] = "WEAK"
            rating["reason"] = (rating.get("reason") or "") + " Index proxy — capped WEAK."
        books.append(rating)
        _log(f"{book_id} n={len(trades)} rating={rating.get('rating')} oos={rating.get('oos')}")

    # Teacher-faithful ST flip
    st = supertrend(bars_3m, 10, 3.0)
    book_id = "MIX-SLTP-ST-FLIP/NIFTY/ST10x3"
    trades_st = simulate_st_flip_exit(
        bars_3m,
        leans,
        st,
        strategy_id=book_id,
        underlying=underlying,
        use_009=True,
    )
    rating_st = rate_trades(trades_st, book_id=book_id)
    rating_st.update(
        {
            "mix_id": "MIX-SLTP-ST-FLIP",
            "entry": "STRAT-003_all_three_INDEX_3m_proxy",
            "exit": "close_through_supertrend",
            "pnl_unit": "UNDERLYING_POINTS_PROXY",
            "promote": False,
            "validated": False,
            "keep_current_strategy": True,
            "reason_breakdown": _reason_breakdown(trades_st),
            "honesty": "ST params WEAK (spoken 103). INDEX not FUTIDX.",
        }
    )
    if rating_st.get("rating") == "CANDIDATE":
        rating_st["rating"] = "WEAK"
    books.append(rating_st)
    _log(f"{book_id} n={len(trades_st)} rating={rating_st.get('rating')}")

    books.append(
        {
            "book_id": "MIX-DESK-IQ-ATR-RR2/NIFTY/OPTION_COST",
            "mix_id": "MIX-DESK-IQ-ATR-RR2",
            "rating": "DATA_INSUFFICIENT",
            "validated": False,
            "promote": False,
            "keep_current_strategy": True,
            "reason": (
                "HYPOTHESIS_OPTION_RT_1PCT applies to option premium pts, not INDEX level. "
                "Rolling OPTIDX SL/TP overlay not run this pass."
            ),
            "costs": "NOT_APPLICABLE_ON_INDEX_PROXY",
        }
    )

    report: dict[str, Any] = {
        "kind": "BACKTEST_SLTP",
        "date": datetime.now(IST).date().isoformat(),
        "underlying": underlying,
        "years": years,
        "interval_resampled_min": 3,
        "bars_1m": len(bars_1m),
        "bars_3m": len(bars_3m),
        "research_ready_for_programming": False,
        "promote": False,
        "keep_current_strategy": True,
        "entry_note": "Reuses STRAT-003 all_three lean as entry proxy; exit overlay is the MIX under test.",
        "gex": "DATA_INSUFFICIENT_NIFTY",
        "books": books,
        "headline": _headline(books),
    }

    out = repo_root() / "data" / "recon" / f"BACKTEST_SLTP_{report['date']}.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    _log(f"wrote {out}")
    return report


def _headline(books: list[dict]) -> str:
    bits = []
    for b in books:
        oos = b.get("oos") or {}
        bits.append(
            f"{b.get('mix_id')}:{b.get('rating')} oos_n={oos.get('n')} wr={oos.get('win_rate')}"
        )
    return " | ".join(bits)
