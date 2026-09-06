"""Paginate HQ /charts/intraday in 90-day windows. Cache under data/recon/ohlc/."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from dhan_client.client import DhanClient
from dhan_client.config import repo_root
from dhan_client.errors import DhanApiError
from dhan_client.logging_util import get_logger

from backtest_engine.indicators import Bar, bars_from_chart

log = get_logger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))
CHUNK_DAYS = 90
INDEX_YAML = (("NIFTY", "13", "IDX_I", "INDEX"), ("BANKNIFTY", "25", "IDX_I", "INDEX"), ("SENSEX", "51", "IDX_I", "INDEX"))


def _cache_dir() -> Path:
    path = repo_root() / "data" / "recon" / "ohlc"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _windows(end: datetime, years: float) -> list[tuple[datetime, datetime]]:
    start = end - timedelta(days=int(years * 365))
    out: list[tuple[datetime, datetime]] = []
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=CHUNK_DAYS), end)
        out.append((cur, nxt))
        cur = nxt
    return out


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fetch_chunk(
    client: DhanClient,
    *,
    security_id: str,
    exchange_segment: str,
    instrument: str,
    interval: int,
    from_dt: datetime,
    to_dt: datetime,
    oi: bool = False,
) -> tuple[list[Bar], Optional[str]]:
    cache = _cache_dir() / (
        f"{instrument}_{exchange_segment}_{security_id}_{interval}_"
        f"{from_dt.date().isoformat()}_{to_dt.date().isoformat()}.json"
    )
    if cache.is_file():
        raw = json.loads(cache.read_text(encoding="utf-8"))
        return bars_from_chart(raw), None
    body: dict[str, Any] = {
        "securityId": str(security_id),
        "exchangeSegment": exchange_segment,
        "instrument": instrument,
        "interval": interval,
        "fromDate": _fmt(from_dt),
        "toDate": _fmt(to_dt),
    }
    if oi:
        body["oi"] = True
    try:
        raw = client.historical.intraday(body)
    except DhanApiError as exc:
        return [], f"{exc.error_code or 'ERR'}:{exc}"
    if not isinstance(raw, dict) or not raw.get("timestamp"):
        return [], "empty"
    cache.write_text(json.dumps(raw), encoding="utf-8")
    return bars_from_chart(raw), None


def load_cached_series(
    *,
    security_id: str,
    exchange_segment: str,
    instrument: str,
    interval: int,
) -> list[Bar]:
    """Merge every on-disk chunk for this series. Window dates may drift day-to-day."""
    prefix = f"{instrument}_{exchange_segment}_{security_id}_{interval}_"
    merged: dict[int, Bar] = {}
    for path in _cache_dir().glob(f"{prefix}*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        for bar in bars_from_chart(raw):
            merged[bar.ts] = bar
    return [merged[k] for k in sorted(merged)]


def fetch_range(
    client: DhanClient,
    *,
    security_id: str,
    exchange_segment: str,
    instrument: str,
    interval: int,
    years: float,
    oi: bool = False,
) -> dict[str, Any]:
    cached = load_cached_series(
        security_id=str(security_id),
        exchange_segment=exchange_segment,
        instrument=instrument,
        interval=interval,
    )
    end = datetime.now(IST).replace(hour=15, minute=40, second=0, microsecond=0)
    start = end - timedelta(days=int(years * 365))
    if cached and cached[0].ts <= int(start.timestamp()) + 14 * 86400:
        return {
            "security_id": str(security_id),
            "exchange_segment": exchange_segment,
            "instrument": instrument,
            "interval": interval,
            "years_requested": years,
            "bar_count": len(cached),
            "chunks_ok": 0,
            "errors": [],
            "error_count": 0,
            "from_ts": cached[0].ts,
            "to_ts": cached[-1].ts,
            "has_volume": any(b.volume > 0 for b in cached),
            "bars": cached,
            "cache_reuse": True,
        }
    merged: dict[int, Bar] = {b.ts: b for b in cached}
    errors: list[str] = []
    chunks_ok = 0
    for a, b in _windows(end, years):
        bars, err = fetch_chunk(
            client,
            security_id=security_id,
            exchange_segment=exchange_segment,
            instrument=instrument,
            interval=interval,
            from_dt=a,
            to_dt=b,
            oi=oi,
        )
        if err:
            errors.append(f"{a.date()}..{b.date()}:{err}")
            continue
        chunks_ok += 1
        for bar in bars:
            merged[bar.ts] = bar
    ordered = [merged[k] for k in sorted(merged)]
    return {
        "security_id": str(security_id),
        "exchange_segment": exchange_segment,
        "instrument": instrument,
        "interval": interval,
        "years_requested": years,
        "bar_count": len(ordered),
        "chunks_ok": chunks_ok,
        "errors": errors[:12],
        "error_count": len(errors),
        "from_ts": ordered[0].ts if ordered else None,
        "to_ts": ordered[-1].ts if ordered else None,
        "has_volume": any(b.volume > 0 for b in ordered),
        "bars": ordered,
    }
