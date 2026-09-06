"""NIFTY INDEX OHLC proxies for Chart Fanatics Carmine + Jadecap MIX-CF-* books.

Honesty: ASR guests; structure proxies only; OF absorb + Asia sessions = DI;
no promote; no wr claim.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.cf_carmine_jadecap_proxy import (
    gap_summary_carmine_jadecap,
    lean_cf_carmine_fail_break,
    lean_cf_carmine_open_hold,
    lean_cf_jadecap_fvg_draw,
    lean_cf_jadecap_swing_fail,
)
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.paper_watch import append_paper_event
from backtest_engine.rating import rate_trades
from backtest_engine.resample import resample
from backtest_engine.simulate import simulate_leans

IST = timezone(timedelta(hours=5, minutes=30))
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}


def _log(msg: str) -> None:
    print(f"[cf-carmine-jadecap] {msg}", file=sys.stderr, flush=True)


def run_cf_carmine_jadecap(
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
    gaps = gap_summary_carmine_jadecap()

    books.append(
        {
            "book_id": "MIX-CF-CARMINE-ABSORB/proxy/OF_REQUIRED",
            "rating": "DATA_INSUFFICIENT",
            "reason": "Absorption needs DOM/heatmap/footprint delta — no India tape; PARKED.",
            "promote": False,
            "validated": False,
            "customer_default": False,
            "gaps": gaps,
            "note": "Do not invent synthetic delta from OHLC",
            "transcript_source": "ASR_WHISPER",
        }
    )
    books.append(
        {
            "book_id": "MIX-CF-JADECAP-SESSION-LIQ/proxy/ASIA_LONDON_NY",
            "rating": "DATA_INSUFFICIENT",
            "reason": "Asia/London/NY session boxes + midnight open unmapped to NSE.",
            "promote": False,
            "validated": False,
            "customer_default": False,
            "gaps": gaps,
            "note": "Do not invent Globex session ranges for cash INDEX",
            "transcript_source": "ASR_WHISPER",
        }
    )

    arms = [
        (
            "MIX-CF-CARMINE-FAIL-BREAK/proxy/PDH_PDL_RECLAIM",
            lean_cf_carmine_fail_break(bars_3m),
            "ASR Carmine stop-hunt fail-break; OF volume-tail missing; ET→NSE DI",
        ),
        (
            "MIX-CF-CARMINE-OPEN-HOLD/proxy/SESSION_OPEN_HOLD",
            lean_cf_carmine_open_hold(bars_3m),
            "ASR Carmine open-print hold; OF aggression missing; IST early window stand-in",
        ),
        (
            "MIX-CF-JADECAP-SWING-FAIL/proxy/PDH_PDL_CLOSE_RECLAIM",
            lean_cf_jadecap_swing_fail(bars_3m),
            "ASR Jadecap swing-failure homework; 15m–1H→3m stand-in; separate from Carmine/Marco",
        ),
        (
            "MIX-CF-JADECAP-FVG-DRAW/proxy/SWEEP_THEN_FVG",
            lean_cf_jadecap_fvg_draw(bars_3m),
            "ASR Jadecap liq→inefficiency; 3-candle FVG only; breaker/turtle soup not frozen",
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
        "origin": "EXTERNAL_RESEARCH_Phase8_Carmine_Jadecap_ASR",
        "promote": False,
        "research_ready_for_programming": False,
        "gaps": gaps,
        "books": books,
    }

    out = repo_root() / "data" / "recon" / "BACKTEST_CF_CARMINE_JADECAP_2026-09-06.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    _log(f"wrote {out}")
    return report
