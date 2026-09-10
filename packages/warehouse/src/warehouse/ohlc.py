"""Multi-timeframe INDEX OHLC: HQ fetch + resample. No orders. No poll loop.

HQ SOURCE_FACT intervals: 1, 5, 15, 25, 60 (intraday) and daily historical.
3m is 1m resample (spoken STRAT-003). 1w is daily resample. Neither is an HQ enum.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

IST = timezone(timedelta(hours=5, minutes=30))

# Canonical names used in ohlc_bars.timeframe
TIMEFRAMES = ("1m", "3m", "5m", "15m", "60m", "1d", "1w")
HQ_INTRADAY = {"1m": 1, "5m": 5, "15m": 15, "60m": 60}
RESAMPLED = {
    "3m": ("1m", 3, "minute"),
    "1w": ("1d", 7, "week"),
}
INDEX_HINTS = {
    "NIFTY": ("13", "IDX_I"),
    "BANKNIFTY": ("25", "IDX_I"),
    "SENSEX": ("51", "IDX_I"),
}


def normalize_tf(raw: str) -> str:
    key = str(raw or "").strip().lower().replace(" ", "")
    aliases = {
        "1": "1m",
        "1min": "1m",
        "3": "3m",
        "3min": "3m",
        "5": "5m",
        "5min": "5m",
        "15": "15m",
        "15min": "15m",
        "60": "60m",
        "60m": "60m",
        "1h": "60m",
        "hour": "60m",
        "1hour": "60m",
        "d": "1d",
        "day": "1d",
        "daily": "1d",
        "1day": "1d",
        "w": "1w",
        "week": "1w",
        "weekly": "1w",
        "1week": "1w",
    }
    out = aliases.get(key, key)
    if out not in TIMEFRAMES:
        raise ValueError(f"unknown timeframe {raw!r}; use {TIMEFRAMES}")
    return out


def origin_for(tf: str) -> str:
    if tf in RESAMPLED:
        return f"resample_{RESAMPLED[tf][0]}"
    if tf == "1d":
        return "dhan_daily"
    return f"dhan_intraday_{HQ_INTRADAY[tf]}"


def unwrap_chart(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    if isinstance(data, dict) and (
        "close" in data or "open" in data or "Close" in data or "timestamp" in data
    ):
        return data
    if "close" in payload or "timestamp" in payload:
        return payload
    return {}


def rows_from_chart(payload: Any) -> list[dict[str, Any]]:
    data = unwrap_chart(payload)
    opens = data.get("open") or data.get("Open") or []
    highs = data.get("high") or data.get("High") or []
    lows = data.get("low") or data.get("Low") or []
    closes = data.get("close") or data.get("Close") or []
    ts = data.get("timestamp") or data.get("time") or []
    vols = data.get("volume") or data.get("Volume") or []
    ois = data.get("open_interest") or data.get("oi") or []
    n = min(len(opens), len(highs), len(lows), len(closes), len(ts))
    if n == 0:
        return []
    if len(vols) < n:
        vols = list(vols) + [0] * (n - len(vols))
    out: list[dict[str, Any]] = []
    for i in range(n):
        try:
            row = {
                "ts": int(float(ts[i])),
                "open": float(opens[i]),
                "high": float(highs[i]),
                "low": float(lows[i]),
                "close": float(closes[i]),
                "volume": float(vols[i] or 0),
                "oi": None,
            }
        except (TypeError, ValueError):
            continue
        if i < len(ois):
            try:
                row["oi"] = float(ois[i]) if ois[i] not in (None, "") else None
            except (TypeError, ValueError):
                row["oi"] = None
        out.append(row)
    return out


def ts_iso(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()


def resample_minutes(rows: Iterable[dict[str, Any]], minutes: int) -> list[dict[str, Any]]:
    if minutes <= 1:
        return list(rows)
    bucket = minutes * 60
    groups: dict[int, list[dict[str, Any]]] = {}
    order: list[int] = []
    for row in rows:
        key = (int(row["ts"]) // bucket) * bucket
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)
    out: list[dict[str, Any]] = []
    for key in order:
        chunk = groups[key]
        oi_vals = [c["oi"] for c in chunk if c.get("oi") is not None]
        out.append(
            {
                "ts": key,
                "open": chunk[0]["open"],
                "high": max(c["high"] for c in chunk),
                "low": min(c["low"] for c in chunk),
                "close": chunk[-1]["close"],
                "volume": sum(c.get("volume") or 0 for c in chunk),
                "oi": oi_vals[-1] if oi_vals else None,
            }
        )
    return out


def resample_weeks(daily: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[int, list[dict[str, Any]]] = {}
    order: list[int] = []
    for row in daily:
        dt = datetime.fromtimestamp(int(row["ts"]), tz=timezone.utc)
        monday = (dt - timedelta(days=dt.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        key = int(monday.timestamp())
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)
    out: list[dict[str, Any]] = []
    for key in order:
        chunk = groups[key]
        oi_vals = [c["oi"] for c in chunk if c.get("oi") is not None]
        out.append(
            {
                "ts": key,
                "open": chunk[0]["open"],
                "high": max(c["high"] for c in chunk),
                "low": min(c["low"] for c in chunk),
                "close": chunk[-1]["close"],
                "volume": sum(c.get("volume") or 0 for c in chunk),
                "oi": oi_vals[-1] if oi_vals else None,
            }
        )
    return out


def fetch_hq_chart(
    client: Any,
    *,
    underlying: str,
    timeframe: str,
    from_dt: datetime,
    to_dt: datetime,
) -> tuple[list[dict[str, Any]], Optional[str]]:
    """One Dhan chart call. timeframe must be HQ (1m/5m/15m/60m/1d)."""
    hint = INDEX_HINTS.get(underlying.upper())
    if hint is None:
        return [], f"UNKNOWN underlying {underlying}"
    sid, seg = hint
    tf = normalize_tf(timeframe)
    try:
        if tf == "1d":
            raw = client.historical.daily(
                {
                    "securityId": sid,
                    "exchangeSegment": seg,
                    "instrument": "INDEX",
                    "fromDate": from_dt.strftime("%Y-%m-%d"),
                    "toDate": to_dt.strftime("%Y-%m-%d"),
                }
            )
        elif tf in HQ_INTRADAY:
            raw = client.historical.intraday(
                {
                    "securityId": sid,
                    "exchangeSegment": seg,
                    "instrument": "INDEX",
                    "interval": HQ_INTRADAY[tf],
                    "fromDate": from_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "toDate": to_dt.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        else:
            return [], f"not an HQ interval: {tf}"
    except Exception as exc:  # noqa: BLE001
        return [], f"{type(exc).__name__}"
    rows = rows_from_chart(raw)
    if not rows:
        return [], "empty/unparsed"
    return rows, None
