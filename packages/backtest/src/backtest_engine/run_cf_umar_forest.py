"""NIFTY INDEX OHLC proxies for Chart Fanatics Umar + Forest MIX-CF-* books.

Honesty: ASR guests; structure / bar-vol proxies only; no promote; no wr claim.
Opening drive = DATA_INSUFFICIENT. True VAP / OF = not claimed.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.cf_umar_forest_proxy import (
    gap_summary_umar_forest,
    lean_cf_forest_poc_retest,
    lean_cf_forest_vpe_edge,
    lean_cf_umar_morning_top,
)
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.paper_watch import append_paper_event
from backtest_engine.rating import rate_trades
from backtest_engine.resample import resample
from backtest_engine.simulate import simulate_leans

IST = timezone(timedelta(hours=5, minutes=30))
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}


def _log(msg: str) -> None:
    print(f"[cf-umar-forest] {msg}", file=sys.stderr, flush=True)


def run_cf_umar_forest(
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
    gaps = gap_summary_umar_forest()

    # Opening drive — honest DI book, no invented leans
    books.append(
        {
            "book_id": "MIX-CF-UMAR-OPENING-DRIVE/proxy/NAMED_ONLY",
            "rating": "DATA_INSUFFICIENT",
            "reason": "Opening drive named; OF deep-dive deferred on ASR video — no entry recipe.",
            "promote": False,
            "validated": False,
            "customer_default": False,
            "gaps": gaps,
            "note": "Do not invent ORB/drive from other guests",
            "transcript_source": "ASR_WHISPER",
        }
    )

    arms = [
        (
            "MIX-CF-UMAR-MORNING-TOP/proxy/GAP_FAIL_BOUNCE",
            lean_cf_umar_morning_top(bars_3m),
            "ASR Umar morning top; OF missing; ET→NSE unmapped; IST early window stand-in",
        ),
        (
            "MIX-CF-FOREST-VPE-EDGE/proxy/PDH_PDL_RELVOL",
            lean_cf_forest_vpe_edge(bars_3m),
            "ASR Forest VPE edge; overnight DI; true HVN VAP missing; PDH/PDL+relvol only",
        ),
        (
            "MIX-CF-FOREST-POC-RETEST/proxy/BIN_POC_VAL",
            lean_cf_forest_poc_retest(bars_3m),
            "ASR Forest prior POC/VAL; PROJECT bin profile not exchange VAP",
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
        rating["session_transfer"] = "US_NY_TO_NSE_DATA_INSUFFICIENT"
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
        "origin": "EXTERNAL_RESEARCH_Phase7_Umar_Forest_ASR",
        "promote": False,
        "research_ready_for_programming": False,
        "gaps": gaps,
        "books": books,
    }

    out = repo_root() / "data" / "recon" / "BACKTEST_CF_UMAR_FOREST_2026-09-06.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    _log(f"wrote {out}")
    return report
