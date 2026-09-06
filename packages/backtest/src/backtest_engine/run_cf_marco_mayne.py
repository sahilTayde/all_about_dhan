"""NIFTY INDEX OHLC proxies for Chart Fanatics Marco + Mayne MIX-CF-* books.

Honesty: ASR guests; structure proxies only; no promote; no wr claim.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.cf_marco_mayne_proxy import (
    gap_summary_marco_mayne,
    lean_cf_marco_eq_sweep,
    lean_cf_marco_sweep_reclaim,
    lean_cf_mayne_breaker,
    lean_cf_mayne_msb_discount,
)
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.paper_watch import append_paper_event
from backtest_engine.rating import rate_trades
from backtest_engine.resample import resample
from backtest_engine.simulate import simulate_leans

IST = timezone(timedelta(hours=5, minutes=30))
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}


def _log(msg: str) -> None:
    print(f"[cf-marco-mayne] {msg}", file=sys.stderr, flush=True)


def run_cf_marco_mayne(
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
    gaps = gap_summary_marco_mayne()

    arms = [
        (
            "MIX-CF-MARCO-LIQ-TRAP/proxy/SWEEP_RECLAIM",
            lean_cf_marco_sweep_reclaim(bars_3m),
            "ASR Marco liquidity trap structure proxy",
        ),
        (
            "MIX-CF-MARCO-INT-EXT/proxy/EQ_SWEEP",
            lean_cf_marco_eq_sweep(bars_3m),
            "ASR Marco equal-extreme / int→ext proxy; NY clock unmapped",
        ),
        (
            "MIX-CF-MAYNE-ICT-HTF/proxy/MSB_DISCOUNT",
            lean_cf_mayne_msb_discount(bars_3m),
            "ASR Mayne MSB + discount half-range proxy; OB combine not frozen",
        ),
        (
            "MIX-CF-MAYNE-BREAKER/proxy/BREAKER",
            lean_cf_mayne_breaker(bars_3m),
            "ASR Mayne breaker proxy; HTF OB gate missing",
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
        rating["promote"] = False
        rating["validated"] = False
        rating["customer_default"] = False
        rating["signal_bars"] = n_sig
        rating["trade_n"] = len(trades)
        rating["gaps"] = gaps
        rating["note"] = note
        rating["unit"] = "INDEX_POINTS_PROXY_NOT_OPTION_PREMIUM"
        rating["session_transfer"] = "US_CRYPTO_TO_NSE_DATA_INSUFFICIENT"
        rating["transcript_source"] = "ASR_WHISPER"
        if rating.get("rating") == "CANDIDATE":
            rating["rating"] = "WEAK"
            rating["reason"] = (
                (rating.get("reason") or "")
                + " ASR guest proxy; transfer unresolved — not CANDIDATE."
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
        "origin": "EXTERNAL_RESEARCH_Phase4_Marco_Mayne_ASR",
        "promote": False,
        "research_ready_for_programming": False,
        "gaps": gaps,
        "books": books,
    }

    out = repo_root() / "data" / "recon" / "BACKTEST_CF_MARCO_MAYNE_2026-09-06.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    _log(f"wrote {out}")
    return report
