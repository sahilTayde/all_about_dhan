"""NIFTY INDEX OHLC proxy for Chart Fanatics Fabio MIX-CF-* books.

Honesty: teacher OF trigger PARKED. Structure proxies only. No promote. No wr claim.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.fabio_proxy import (
    gap_summary,
    lean_cf_break_retest_pd,
    lean_cf_failed_auction,
    lean_cf_mr_to_poc,
)
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.paper_watch import append_paper_event
from backtest_engine.rating import rate_trades
from backtest_engine.resample import resample
from backtest_engine.simulate import simulate_leans

IST = timezone(timedelta(hours=5, minutes=30))
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}


def _log(msg: str) -> None:
    print(f"[cf-fabio] {msg}", file=sys.stderr, flush=True)


def run_cf_fabio(
    client: DhanClient,
    *,
    years: float = 2.0,
    interval: int = 1,
    underlying: str = "NIFTY",
) -> dict[str, Any]:
    _, sid, seg, inst = INDEX_BY_NAME[underlying]
    _log(f"fetch {underlying} years={years} (cache OK)")
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

    books: list[dict[str, Any]] = []
    gaps = gap_summary()

    arms = [
        (
            "MIX-CF-FABIO-TREND-NY/proxy/FAILED_AUCTION",
            lean_cf_failed_auction(bars_3m),
            "PARKED_OF + BACKTEST_BOOK structure",
        ),
        (
            "MIX-CF-FABIO-TREND-NY/proxy/BREAK_RETEST_PD",
            lean_cf_break_retest_pd(bars_3m),
            "PARKED_OF + BACKTEST_BOOK structure",
        ),
        (
            "MIX-CF-FABIO-MR-RANGE/proxy/MR_TO_POC",
            lean_cf_mr_to_poc(bars_3m),
            "PARKED_OF + BACKTEST_BOOK profile proxy",
        ),
    ]

    for book_id, leans, note in arms:
        n_sig = sum(1 for x in leans if x in ("CE", "PE"))
        if len(bars_3m) < 50:
            books.append(
                {
                    "book_id": book_id,
                    "rating": "DATA_INSUFFICIENT",
                    "reason": "Too few INDEX bars in cache/fixtures.",
                    "promote": False,
                    "validated": False,
                    "gaps": gaps,
                    "note": note,
                }
            )
            continue
        trades = simulate_leans(
            bars_3m,
            leans,
            strategy_id=book_id,
            underlying=underlying,
            use_009=True,
        )
        rating = rate_trades(trades, book_id=book_id)
        # Never promote; force honesty on OF gap
        rating["promote"] = False
        rating["validated"] = False
        rating["customer_default"] = False
        rating["signal_bars"] = n_sig
        rating["trade_n"] = len(trades)
        rating["gaps"] = gaps
        rating["note"] = note
        rating["unit"] = "INDEX_POINTS_PROXY_NOT_OPTION_PREMIUM"
        rating["session_transfer"] = "NY_LONDON_TO_NSE_DATA_INSUFFICIENT"
        if rating.get("rating") == "CANDIDATE":
            rating["rating"] = "WEAK"
            rating["reason"] = (
                (rating.get("reason") or "")
                + " OF trigger absent; US→NSE transfer unresolved — not CANDIDATE."
            )
        books.append(rating)
        append_paper_event(
            book_id.split("/")[0],
            {
                "event": "proxy_backtest_tick",
                "book_id": book_id,
                "trade_n": len(trades),
                "rating": rating.get("rating"),
                "wr": (rating.get("is") or {}).get("win_rate"),
            },
        )

    report: dict[str, Any] = {
        "as_of_ist": datetime.now(IST).isoformat(),
        "underlying": underlying,
        "years": years,
        "bars_1m": len(bars_1m),
        "bars_3m": len(bars_3m),
        "origin": "EXTERNAL_RESEARCH_tvERE-Beu2U_Fabio",
        "teacher_of_status": "PARKED_DATA_INSUFFICIENT",
        "promote": False,
        "research_ready_for_programming": False,
        "gaps": gaps,
        "books": books,
    }

    out = repo_root() / "data" / "recon" / "BACKTEST_CF_FABIO_2026-09-06.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    _log(f"wrote {out}")
    return report
