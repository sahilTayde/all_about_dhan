"""Rolling OPTIDX premium bars. 30-day chunks. Data API 5/s."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from dhan_client.client import DhanClient
from dhan_client.config import repo_root
from dhan_client.errors import DhanApiError

from backtest_engine.indicators import Bar

IST = timezone(timedelta(hours=5, minutes=30))
CHUNK_DAYS = 30
REQUIRED = ["open", "high", "low", "close", "volume"]

UNDERLYINGS = (
    ("NIFTY", "13", "NSE_FNO"),
    ("BANKNIFTY", "25", "NSE_FNO"),
    ("SENSEX", "51", "BSE_FNO"),
)


def _cache_dir() -> Path:
    path = repo_root() / "data" / "recon" / "ohlc" / "rolling"
    path.mkdir(parents=True, exist_ok=True)
    return path


def bars_from_rolling(payload: dict, *, side: str) -> list[Bar]:
    """Parse data.ce or data.pe arrays. side is 'ce' or 'pe'."""
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    block = (data or {}).get(side) if isinstance(data, dict) else None
    if not isinstance(block, dict):
        return []
    opens = block.get("open") or []
    highs = block.get("high") or []
    lows = block.get("low") or []
    closes = block.get("close") or []
    vols = block.get("volume") or []
    ts = block.get("timestamp") or []
    n = min(len(opens), len(highs), len(lows), len(closes), len(ts))
    if not n:
        return []
    if len(vols) < n:
        vols = list(vols) + [0] * (n - len(vols))
    out: list[Bar] = []
    for i in range(n):
        if opens[i] is None or closes[i] is None:
            continue
        out.append(
            Bar(
                ts=int(ts[i]),
                open=float(opens[i]),
                high=float(highs[i] if highs[i] is not None else opens[i]),
                low=float(lows[i] if lows[i] is not None else opens[i]),
                close=float(closes[i]),
                volume=float(vols[i] or 0),
            )
        )
    return out


def fetch_rolling_range(
    client: DhanClient,
    *,
    security_id: str,
    exchange_segment: str,
    strike: str,
    option_type: str,
    interval: int = 5,
    years: float = 1.0,
    expiry_flag: str = "WEEK",
    expiry_code: int = 1,
) -> dict[str, Any]:
    end = datetime.now(IST).date()
    start = end - timedelta(days=int(years * 365))
    side = "ce" if option_type.upper() == "CALL" else "pe"
    prefix = (
        f"{exchange_segment}_{security_id}_{expiry_flag}_{expiry_code}_"
        f"{strike}_{option_type}_{interval}_"
    )
    merged: dict[int, Bar] = {}
    for path in _cache_dir().glob(f"{prefix}*.json"):
        raw_cached = json.loads(path.read_text(encoding="utf-8"))
        bars_c = bars_from_rolling(raw_cached, side=side)
        if not bars_c:
            bars_c = bars_from_rolling(raw_cached, side="ce") or bars_from_rolling(
                raw_cached, side="pe"
            )
        for bar in bars_c:
            merged[bar.ts] = bar
    if merged:
        ordered_cached = [merged[k] for k in sorted(merged)]
        first = datetime.fromtimestamp(ordered_cached[0].ts, tz=IST).date()
        if first <= start + timedelta(days=14):
            return {
                "security_id": str(security_id),
                "exchange_segment": exchange_segment,
                "strike": strike,
                "drvOptionType": option_type.upper(),
                "expiry_flag": expiry_flag,
                "interval": interval,
                "bar_count": len(ordered_cached),
                "chunks_ok": 0,
                "error_count": 0,
                "errors": [],
                "bars": ordered_cached,
                "cache_reuse": True,
            }
    errors: list[str] = []
    chunks_ok = 0
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=CHUNK_DAYS), end)
        cache = _cache_dir() / (
            f"{exchange_segment}_{security_id}_{expiry_flag}_{expiry_code}_"
            f"{strike}_{option_type}_{interval}_{cur.isoformat()}_{nxt.isoformat()}.json"
        )
        raw: Optional[dict] = None
        print(
            f"[rolling] {option_type} {strike} {expiry_flag} {cur}..{nxt} "
            f"{'cache' if cache.is_file() else 'GET'}",
            file=sys.stderr,
            flush=True,
        )
        if cache.is_file():
            raw = json.loads(cache.read_text(encoding="utf-8"))
        else:
            body = {
                "exchangeSegment": exchange_segment,
                "interval": interval,
                "securityId": str(security_id),
                "instrument": "OPTIDX",
                "expiryFlag": expiry_flag,
                "expiryCode": expiry_code,
                "strike": strike,
                "drvOptionType": option_type.upper(),
                "requiredData": REQUIRED,
                "fromDate": cur.isoformat(),
                "toDate": nxt.isoformat(),
            }
            try:
                raw = client.historical.rolling_option(body)
                cache.write_text(json.dumps(raw), encoding="utf-8")
            except DhanApiError as exc:
                errors.append(f"{cur}..{nxt}:{exc.error_code or 'ERR'}:{exc}")
                raw = None
        if raw:
            bars = bars_from_rolling(raw, side=side)
            if not bars:
                # CALL request may still nest under data.ce
                bars = bars_from_rolling(raw, side="ce") or bars_from_rolling(raw, side="pe")
            if bars:
                chunks_ok += 1
                for bar in bars:
                    merged[bar.ts] = bar
            else:
                errors.append(f"{cur}..{nxt}:empty")
        cur = nxt
    ordered = [merged[k] for k in sorted(merged)]
    return {
        "security_id": str(security_id),
        "exchange_segment": exchange_segment,
        "strike": strike,
        "drvOptionType": option_type.upper(),
        "expiry_flag": expiry_flag,
        "interval": interval,
        "bar_count": len(ordered),
        "chunks_ok": chunks_ok,
        "error_count": len(errors),
        "errors": errors[:8],
        "bars": ordered,
    }
