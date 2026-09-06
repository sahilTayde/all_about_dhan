"""Stitch listed FUTIDX contracts into a front-month tape.

Scrip-master is live IDs only. Expired-month history is DATA_INSUFFICIENT
unless HQ still serves those security IDs. Spoken STRAT-003 is 3m FUTIDX.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.futidx import FutIdxContract, parse_all_futidx_csv

from backtest_engine.fetch import fetch_range
from backtest_engine.indicators import Bar

IST = timezone(timedelta(hours=5, minutes=30))
MIN_CONTINUOUS_DAYS = 365


def stitch_front_month(
    series: list[tuple[FutIdxContract, list[Bar]]],
) -> list[Bar]:
    """At each ts pick the nearest-expiry contract that is still unexpired that day."""
    if not series:
        return []
    by_ts: dict[int, list[tuple[str, Bar]]] = {}
    for contract, bars in series:
        exp = contract.expiry
        for bar in bars:
            day = datetime.fromtimestamp(bar.ts, tz=IST).date().isoformat()
            if day > exp:
                continue
            by_ts.setdefault(bar.ts, []).append((exp, bar))
    out: list[Bar] = []
    for ts in sorted(by_ts):
        rows = by_ts[ts]
        rows.sort(key=lambda item: item[0])
        out.append(rows[0][1])
    return out


def fetch_listed_futidx(
    client: DhanClient,
    *,
    years: float,
    interval: int = 1,
) -> dict[str, Any]:
    try:
        text = client.instruments.fetch_scrip_master_text(detailed=True)
        all_contracts = parse_all_futidx_csv(text)
        if not all_contracts:
            compact = client.instruments.fetch_scrip_master_text(detailed=False)
            all_contracts = parse_all_futidx_csv(compact)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "by_name": {}}

    by_name: dict[str, Any] = {}
    for name, contracts in all_contracts.items():
        fetched: list[tuple[FutIdxContract, list[Bar]]] = []
        meta: list[dict[str, Any]] = []
        for contract in contracts:
            series = fetch_range(
                client,
                security_id=contract.security_id,
                exchange_segment=contract.exchange_segment,
                instrument="FUTIDX",
                interval=interval,
                years=years,
                oi=True,
            )
            bars = series.get("bars") or []
            fetched.append((contract, bars))
            meta.append(
                {
                    "security_id": contract.security_id,
                    "expiry": contract.expiry,
                    "symbol": contract.symbol,
                    "bar_count": series.get("bar_count"),
                    "from_ts": series.get("from_ts"),
                    "to_ts": series.get("to_ts"),
                    "error_count": series.get("error_count"),
                    "has_volume": series.get("has_volume"),
                }
            )
        stitched = stitch_front_month(fetched)
        span_days = 0
        if len(stitched) >= 2:
            span_days = (stitched[-1].ts - stitched[0].ts) // 86400
        status = "PARTIAL" if span_days >= MIN_CONTINUOUS_DAYS else "DATA_INSUFFICIENT"
        by_name[name] = {
            "contracts": meta,
            "contract_count": len(contracts),
            "stitched_bars": stitched,
            "stitched_n": len(stitched),
            "span_days": span_days,
            "status": status,
            "note": (
                "Live scrip-master only. No expired-month FUTIDX ID book. "
                "Spoken 003 continuous history stays DATA_INSUFFICIENT unless span ≥ 1y."
            ),
        }
    return {"ok": True, "by_name": by_name}
