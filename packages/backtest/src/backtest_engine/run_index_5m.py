"""Fetch HQ 5m INDEX OHLC and count STRAT-003-style all-three bars. Not option P/L."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from dhan_client.client import DhanClient
from dhan_client.config import repo_root
from dhan_client.errors import DhanApiError

from backtest_engine.indicators import all_three, bars_from_chart

IST = timezone(timedelta(hours=5, minutes=30))
YAML = (("NIFTY", 13), ("BANKNIFTY", 25), ("SENSEX", 51))


def _ist_skip_open(ts: int) -> bool:
    dt = datetime.fromtimestamp(ts, tz=IST)
    minutes = dt.hour * 60 + dt.minute
    return 9 * 60 + 15 <= minutes < 9 * 60 + 45


def _ist_after_flatten(ts: int) -> bool:
    dt = datetime.fromtimestamp(ts, tz=IST)
    minutes = dt.hour * 60 + dt.minute
    return minutes >= 15 * 60 + 15


def run_one(client: DhanClient, name: str, scrip: int, from_d: str, to_d: str) -> dict[str, Any]:
    try:
        raw = client.historical.intraday(
            {
                "securityId": str(scrip),
                "exchangeSegment": "IDX_I",
                "instrument": "INDEX",
                "interval": 5,
                "fromDate": from_d,
                "toDate": to_d,
            }
        )
    except DhanApiError as exc:
        return {
            "underlying": name,
            "scrip": scrip,
            "ok": False,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "message": str(exc),
        }
    bars = bars_from_chart(raw)
    leans = all_three(bars)
    ce = pe = skip = open_skip = flat = 0
    for bar, lean in zip(bars, leans):
        if _ist_skip_open(bar.ts):
            open_skip += 1
            continue
        if _ist_after_flatten(bar.ts):
            flat += 1
            continue
        if lean == "CE":
            ce += 1
        elif lean == "PE":
            pe += 1
        else:
            skip += 1
    return {
        "underlying": name,
        "scrip": scrip,
        "ok": True,
        "interval": 5,
        "instrument": "INDEX",
        "exchangeSegment": "IDX_I",
        "bar_count": len(bars),
        "last_close": bars[-1].close if bars else None,
        "all_three_CE_bars": ce,
        "all_three_PE_bars": pe,
        "skip_disagree_or_warmup": skip,
        "ignored_0915_0945": open_skip,
        "ignored_after_1515": flat,
        "win_rate": None,
        "option_pnl": None,
        "note": (
            "FUTURES_PROXY on INDEX 5m OHLC — not option fills. "
            "Spoken STRAT-003 is 3m FUTIDX; HQ has no 3m. Supertrend 10,3 is inference."
        ),
    }


def run_default(client: DhanClient) -> dict[str, Any]:
    today = datetime.now(IST).date()
    from_d = (today - timedelta(days=7)).isoformat() + " 09:15:00"
    to_d = today.isoformat() + " 15:40:00"
    rows = [run_one(client, name, scrip, from_d, to_d) for name, scrip in YAML]
    report = {
        "as_of_ist": datetime.now(IST).isoformat(),
        "mix": "MIX-DEFAULT-BUY compute on INDEX 5m (not option book)",
        "from": from_d,
        "to": to_d,
        "metrics_claimed": False,
        "books": rows,
    }
    out = repo_root() / "data" / "recon"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"BACKTEST_INDEX_5M_{today.isoformat()}.json"
    path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    report["wrote"] = str(path)
    return report
