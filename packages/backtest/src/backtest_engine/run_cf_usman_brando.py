"""NIFTY INDEX OHLC proxies for Chart Fanatics Usman + Brando MIX-CF-* books.

Honesty: ASR guests; options OI/greeks/news/size mostly DI; structure proxies
only for Brando reclaim/round/bounce; no promote; no wr claim.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.cf_usman_brando_proxy import (
    gap_summary_usman_brando,
    lean_cf_brando_htf_bounce,
    lean_cf_brando_htf_reclaim,
    lean_cf_brando_round_break,
)
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.paper_watch import append_paper_event
from backtest_engine.rating import rate_trades
from backtest_engine.resample import resample
from backtest_engine.simulate import simulate_leans

IST = timezone(timedelta(hours=5, minutes=30))
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}


def _log(msg: str) -> None:
    print(f"[cf-usman-brando] {msg}", file=sys.stderr, flush=True)


def run_cf_usman_brando(
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
    gaps = gap_summary_usman_brando()

    di_arms = [
        (
            "MIX-CF-USMAN-OI-STRIKE/proxy/OPTIDX_OI",
            "Strike pick needs OPTIDX OI/volume — no chain book; DI.",
        ),
        (
            "MIX-CF-USMAN-0DTE-GAMMA/proxy/GREEKS_0DTE",
            "0DTE gamma+IV needs greeks + US/NSE expiry map — DI.",
        ),
        (
            "MIX-CF-USMAN-WEEKLY-SIZE/proxy/PREMIUM_DOW",
            "Weekly Mon–Fri size is management on premium% — DI.",
        ),
        (
            "MIX-CF-USMAN-PRICE-STOP/proxy/LEVEL_STOP",
            "Price/level stops need frozen entry LOI — not spoken; DI.",
        ),
        (
            "MIX-CF-BRANDO-SIZE-ZERO/proxy/PREMIUM_MAXLOSS",
            "Size-for-zero needs OPTIDX premium ledger — DI.",
        ),
        (
            "MIX-CF-BRANDO-NEWS-ALIGN/proxy/LEVEL_PLUS_NEWS",
            "News/Fed/tariff catalyst join unmapped — DI.",
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
                "note": "Do not invent OI/greeks/news from INDEX OHLC",
                "transcript_source": "ASR_WHISPER",
            }
        )

    arms = [
        (
            "MIX-CF-BRANDO-HTF-RECLAIM/proxy/SWING_RECLAIM",
            lean_cf_brando_htf_reclaim(bars_3m),
            "ASR Brando HTF reclaim; multi-year major not modeled; SPX→NIFTY DI",
        ),
        (
            "MIX-CF-BRANDO-ROUND-BREAK/proxy/ROUND100",
            lean_cf_brando_round_break(bars_3m),
            "ASR Brando round break; news catalyst missing; 100-pt NIFTY stand-in",
        ),
        (
            "MIX-CF-BRANDO-HTF-BOUNCE/proxy/SWING_TOUCH_REJECT",
            lean_cf_brando_htf_bounce(bars_3m),
            "ASR Brando HTF bounce/defend; quick-bounce clock not frozen; no news",
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
        rating["session_transfer"] = "US_SPX_OPTIONS_TO_NSE_DATA_INSUFFICIENT"
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
        "origin": "EXTERNAL_RESEARCH_Phase9_Usman_Brando_ASR",
        "promote": False,
        "research_ready_for_programming": False,
        "gaps": gaps,
        "books": books,
    }

    out = repo_root() / "data" / "recon" / "BACKTEST_CF_USMAN_BRANDO_2026-09-06.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    _log(f"wrote {out}")
    return report
