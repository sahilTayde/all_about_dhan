"""NIFTY INDEX OHLC proxies for Chart Fanatics Andrea + Omor MIX-CF-* books.

Honesty: ASR guests; Andrea OF absorb PARKED/DI; Omor KZ/ADR DI;
structure proxies only; no promote; no wr claim; Andrea ≠ Fabio.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.cf_andrea_omor_proxy import (
    gap_summary_andrea_omor,
    lean_cf_andrea_fail_auction,
    lean_cf_andrea_orb_accept,
    lean_cf_andrea_stop_fade,
    lean_cf_omor_mmm_frame,
    lean_cf_omor_ote,
    lean_cf_omor_pdh_reversal,
)
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.paper_watch import append_paper_event
from backtest_engine.rating import rate_trades
from backtest_engine.resample import resample
from backtest_engine.simulate import simulate_leans

IST = timezone(timedelta(hours=5, minutes=30))
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}


def _log(msg: str) -> None:
    print(f"[cf-andrea-omor] {msg}", file=sys.stderr, flush=True)


def run_cf_andrea_omor(
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
    gaps = gap_summary_andrea_omor()

    di_arms = [
        (
            "MIX-CF-ANDREA-ABSORB/proxy/OF_FOOTPRINT",
            "True absorb needs footprint/DOM/bubbles — OF PARKED; DI.",
        ),
        (
            "MIX-CF-OMOR-KZ-ADR/proxy/LONDON_NY_ADR",
            "London/NY killzones + ADR day profile — no IST map; DI.",
        ),
    ]
    for book_id, reason in di_arms:
        books.append(
            {
                "book_id": book_id,
                "rating": "DATA_INSUFFICIENT",
                "reason": reason,
                "promote": False,
                "validated": False,
                "customer_default": False,
                "gaps": gaps,
                "note": "Do not invent OF tape or IST killzones from INDEX OHLC",
                "transcript_source": "ASR_WHISPER",
            }
        )

    arms = [
        (
            "MIX-CF-ANDREA-FAIL-AUCTION/proxy/PD_RANGE_RECLAIM",
            lean_cf_andrea_fail_auction(bars_3m),
            "ASR Andrea failed auction; no VP VA; OF preferred; ES→NIFTY DI",
        ),
        (
            "MIX-CF-ANDREA-ORB-ACCEPT/proxy/ORB_HOLD",
            lean_cf_andrea_orb_accept(bars_3m),
            "ASR Andrea ORB acceptance; IST OR stand-in; no OF bubbles",
        ),
        (
            "MIX-CF-ANDREA-STOP-FADE/proxy/PDH_PDL_FADE",
            lean_cf_andrea_stop_fade(bars_3m),
            "ASR Andrea stop-run fade; short fade ≠ full-day; no cascade tape",
        ),
        (
            "MIX-CF-OMOR-MMM-FRAME/proxy/BIAS_SWEEP_DISPLACE",
            lean_cf_omor_mmm_frame(bars_3m),
            "ASR Omor MMM framework; not OTE entry; FX→NIFTY DI",
        ),
        (
            "MIX-CF-OMOR-OTE/proxy/FIB62_RETRACE",
            lean_cf_omor_ote(bars_3m),
            "ASR Omor OTE ~62%; swing grading weak; RR anecdotes null",
        ),
        (
            "MIX-CF-OMOR-PDH-REVERSAL/proxy/OPEN_NEAR_SWEEP",
            lean_cf_omor_pdh_reversal(bars_3m),
            "ASR Omor open-near PDH/PDL sweep reverse; Asia/London missing",
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
        rating["session_transfer"] = "US_ES_OR_FX_ICT_TO_NSE_DATA_INSUFFICIENT"
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
        "origin": "EXTERNAL_RESEARCH_Phase10_Andrea_Omor_ASR",
        "promote": False,
        "research_ready_for_programming": False,
        "gaps": gaps,
        "books": books,
    }

    out = repo_root() / "data" / "recon" / "BACKTEST_CF_ANDREA_OMOR_2026-09-06.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    _log(f"wrote {out}")
    return report
