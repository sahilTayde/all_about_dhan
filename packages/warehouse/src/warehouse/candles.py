"""One-shot multi-TF candle sync into the warehouse. No poll loop. No orders."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any, Optional

from warehouse.ohlc import (
    HQ_INTRADAY,
    INDEX_HINTS,
    IST,
    fetch_hq_chart,
    normalize_tf,
    origin_for,
    resample_minutes,
    resample_weeks,
)
from warehouse.store import Warehouse

UNDERLYINGS = tuple(INDEX_HINTS.keys())
CALL_GAP_SEC = 0.25  # Data API 5/s


def _windows(now: datetime) -> dict[str, tuple[datetime, datetime]]:
    """How far back we pull each HQ series in one shot."""
    return {
        "1m": (now - timedelta(days=7), now),
        "5m": (now - timedelta(days=30), now),
        "15m": (now - timedelta(days=90), now),
        "60m": (now - timedelta(days=90), now),
        "1d": (now - timedelta(days=365 * 5), now + timedelta(days=1)),
    }


def sync_candles(
    *,
    live: bool,
    warehouse: Optional[Warehouse] = None,
    underlyings: tuple[str, ...] = UNDERLYINGS,
    timeframes: tuple[str, ...] = ("1m", "5m", "15m", "60m", "1d"),
) -> dict[str, Any]:
    """Fetch HQ candles, write them, then resample 3m and 1w. Not a live loop."""
    wh = warehouse or Warehouse()
    wh.init()
    report: dict[str, Any] = {
        "ok": True,
        "live": live,
        "loop_started": False,
        "orders": "refused",
        "note": (
            "HQ intervals are 1/5/15/25/60 + daily. "
            "3m = resample 1m. 1w = resample 1d. INDEX only this ticket."
        ),
        "rows": [],
        "gaps": [],
    }
    if not live:
        report["ok"] = False
        report["gaps"].append("DATA_INSUFFICIENT: pass --live to pull Dhan charts")
        report["status"] = wh.status()
        return report

    try:
        from dhan_client import DhanClient
    except Exception:
        report["ok"] = False
        report["gaps"].append("DATA_INSUFFICIENT: dhan_client missing")
        report["status"] = wh.status()
        return report

    client = DhanClient(dry_run=False)
    if getattr(client.settings, "dry_run", True):
        client.close()
        report["ok"] = False
        report["gaps"].append("DATA_INSUFFICIENT: Dhan dry_run — no chart pull")
        report["status"] = wh.status()
        return report

    now = datetime.now(IST)
    windows = _windows(now)
    fetched: dict[tuple[str, str], list[dict[str, Any]]] = {}
    first = True
    try:
        for und in underlyings:
            for tf in timeframes:
                tf_n = normalize_tf(tf)
                if tf_n not in windows:
                    report["gaps"].append(f"{und} {tf_n}: no HQ window")
                    continue
                if not first:
                    time.sleep(CALL_GAP_SEC)
                first = False
                start, end = windows[tf_n]
                rows, err = fetch_hq_chart(
                    client, underlying=und, timeframe=tf_n, from_dt=start, to_dt=end
                )
                if err:
                    report["gaps"].append(f"{und} {tf_n}: {err}")
                    continue
                n = wh.append_ohlc_rows(
                    symbol=und,
                    timeframe=tf_n,
                    rows=rows,
                    source=origin_for(tf_n),
                    origin=origin_for(tf_n),
                )
                fetched[(und, tf_n)] = rows
                report["rows"].append(
                    {"underlying": und, "timeframe": tf_n, "wrote": n, "origin": origin_for(tf_n)}
                )
    finally:
        client.close()

    for und in underlyings:
        one_m = fetched.get((und, "1m")) or []
        if one_m:
            three = resample_minutes(one_m, 3)
            n = wh.append_ohlc_rows(
                symbol=und,
                timeframe="3m",
                rows=three,
                source="resample_1m",
                origin="resample_1m",
            )
            report["rows"].append(
                {"underlying": und, "timeframe": "3m", "wrote": n, "origin": "resample_1m"}
            )
        else:
            report["gaps"].append(f"{und} 3m: no 1m to resample")
        daily = fetched.get((und, "1d")) or []
        if daily:
            week = resample_weeks(daily)
            n = wh.append_ohlc_rows(
                symbol=und,
                timeframe="1w",
                rows=week,
                source="resample_1d",
                origin="resample_1d",
            )
            report["rows"].append(
                {"underlying": und, "timeframe": "1w", "wrote": n, "origin": "resample_1d"}
            )
        else:
            report["gaps"].append(f"{und} 1w: no 1d to resample")

    report["status"] = wh.status()
    return report


def list_bars(symbol: str, timeframe: str, *, limit: int = 8, warehouse: Optional[Warehouse] = None) -> dict[str, Any]:
    wh = warehouse or Warehouse()
    wh.init()
    tf = normalize_tf(timeframe)
    rows = wh.load_bars(symbol.upper(), tf, limit=limit)
    return {
        "symbol": symbol.upper(),
        "timeframe": tf,
        "hq_interval": HQ_INTRADAY.get(tf),
        "n": len(rows),
        "head": rows[:2],
        "tail": rows[-2:] if len(rows) > 2 else rows,
        "NO_PROMOTE": True,
    }
