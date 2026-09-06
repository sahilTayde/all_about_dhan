"""NIFTY INDEX OHLC proxies for Chart Fanatics TG Capital + Trader Kane MIX-CF-* books.

Honesty: ASR guests; structure proxies only; no promote; no wr claim.
Title 90% (TG) = marketing. SMT arm = DATA_INSUFFICIENT on single INDEX.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.config import repo_root

from backtest_engine.cf_tg_kane_proxy import (
    gap_summary_tg_kane,
    lean_cf_kane_eq50,
    lean_cf_kane_po3_sweep,
    lean_cf_tg_ema_wave,
    lean_cf_tg_trident,
)
from backtest_engine.fetch import INDEX_YAML, fetch_range
from backtest_engine.paper_watch import append_paper_event
from backtest_engine.rating import rate_trades
from backtest_engine.resample import resample
from backtest_engine.simulate import simulate_leans

IST = timezone(timedelta(hours=5, minutes=30))
INDEX_BY_NAME = {row[0]: row for row in INDEX_YAML}


def _log(msg: str) -> None:
    print(f"[cf-tg-kane] {msg}", file=sys.stderr, flush=True)


def run_cf_tg_kane(
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
    gaps = gap_summary_tg_kane()

    arms = [
        (
            "MIX-CF-TG-TRIDENT/proxy/FVG_DOJI_CONFIRM",
            lean_cf_tg_trident(bars_3m),
            "ASR TG trident FVG+doji proxy; London KZ unmapped; 30m→3m stand-in",
        ),
        (
            "MIX-CF-TG-EMA-WAVE/proxy/EMA_STACK_200",
            lean_cf_tg_ema_wave(bars_3m),
            "ASR TG EMA wave+200 bias; mid EMA 13 default (15 UNKNOWN); no KZ",
        ),
        (
            "MIX-CF-KANE-EQ50/proxy/EQ_MID_TOUCH",
            lean_cf_kane_eq50(bars_3m),
            "ASR Kane 50% EQ base-hit; nested EQ / SMT missing",
        ),
        (
            "MIX-CF-KANE-PO3-SMT/proxy/PO3_SWEEP_RECLAIM",
            lean_cf_kane_po3_sweep(bars_3m),
            "ASR Kane PO3 sweep stand-in; true SMT NQ/ES = DATA_INSUFFICIENT",
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
        rating["session_transfer"] = "US_FX_NQ_TO_NSE_DATA_INSUFFICIENT"
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
        "origin": "EXTERNAL_RESEARCH_Phase6_TG_Kane_ASR",
        "promote": False,
        "research_ready_for_programming": False,
        "gaps": gaps,
        "books": books,
    }

    out = repo_root() / "data" / "recon" / "BACKTEST_CF_TG_KANE_2026-09-06.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    _log(f"wrote {out}")
    return report
