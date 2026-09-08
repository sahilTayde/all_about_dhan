"""Fetch INDEX 1m OHLC for paper detectors (Okala / CF). Fail soft.

Uses documented Dhan POST /charts/intraday (interval 1). Not news. Not orders.
Empty / parse fail → DATA_INSUFFICIENT; caller must not invent CE/PE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Optional

from trading_agents_india.session_clock import now_ist

_INDEX_HINTS = {
    "NIFTY": ("13", "IDX_I"),
    "BANKNIFTY": ("25", "IDX_I"),
    "SENSEX": ("51", "IDX_I"),
}


@dataclass
class IndexBarsResult:
    underlying: str
    source: str  # dhan_intraday_1m | unavailable
    bars: list[Any] = field(default_factory=list)
    bar_count: int = 0
    data_gaps: list[str] = field(default_factory=list)
    last_close: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "underlying": self.underlying,
            "source": self.source,
            "bar_count": self.bar_count,
            "last_close": self.last_close,
            "data_gaps": list(self.data_gaps),
        }


def _unwrap_chart(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    if isinstance(data, dict) and (
        "close" in data or "open" in data or "Close" in data
    ):
        return data
    return payload


def _to_bars(payload: dict[str, Any]) -> list[Any]:
    data = _unwrap_chart(payload)
    opens = data.get("open") or data.get("Open") or []
    highs = data.get("high") or data.get("High") or []
    lows = data.get("low") or data.get("Low") or []
    closes = data.get("close") or data.get("Close") or []
    ts = data.get("timestamp") or data.get("time") or []
    vols = data.get("volume") or data.get("Volume") or []
    n = min(len(opens), len(highs), len(lows), len(closes), len(ts))
    if n == 0:
        return []
    if len(vols) < n:
        vols = list(vols) + [0] * (n - len(vols))
    try:
        from backtest_engine.indicators import Bar
    except Exception:  # pragma: no cover
        Bar = None  # type: ignore[assignment]
    out: list[Any] = []
    for i in range(n):
        try:
            row = {
                "ts": int(ts[i]),
                "open": float(opens[i]),
                "high": float(highs[i]),
                "low": float(lows[i]),
                "close": float(closes[i]),
                "volume": float(vols[i] or 0),
            }
        except (TypeError, ValueError):
            continue
        if Bar is not None:
            out.append(Bar(**row))
        else:  # pragma: no cover
            out.append(row)
    return out


def fetch_index_bars(underlying: str, *, prefer_live: bool = False) -> IndexBarsResult:
    """Live INDEX 1m when prefer_live and Dhan tokens work; else DI empty."""
    und = underlying.upper()
    hint = _INDEX_HINTS.get(und)
    if hint is None:
        return IndexBarsResult(
            underlying=und,
            source="unavailable",
            data_gaps=[f"UNKNOWN: no INDEX scrip hint for {und}"],
        )
    if not prefer_live:
        return IndexBarsResult(
            underlying=und,
            source="unavailable",
            data_gaps=[
                "DATA_INSUFFICIENT: INDEX 1m not fetched (live-chain off) — "
                "Okala/CF detectors refuse fake leans"
            ],
        )
    sid, seg = hint
    try:
        from dhan_client import DhanClient  # type: ignore
    except Exception:
        return IndexBarsResult(
            underlying=und,
            source="unavailable",
            data_gaps=["DATA_INSUFFICIENT: dhan_client not importable — INDEX bars skipped"],
        )
    try:
        client = DhanClient(dry_run=False)
        if getattr(client.settings, "dry_run", True):
            client.close()
            return IndexBarsResult(
                underlying=und,
                source="unavailable",
                data_gaps=["DATA_INSUFFICIENT: Dhan dry_run — INDEX bars not live"],
            )
        end = now_ist()
        # Okala min_bars=80; today-only 1m is short before ~10:35 IST.
        start = end - timedelta(days=2)
        body = {
            "securityId": sid,
            "exchangeSegment": seg,
            "instrument": "INDEX",
            "interval": 1,
            "fromDate": start.strftime("%Y-%m-%d") + " 09:15:00",
            "toDate": end.strftime("%Y-%m-%d") + " 15:40:00",
        }
        raw = client.historical.intraday(body)
        client.close()
        bars = _to_bars(raw if isinstance(raw, dict) else {})
        if not bars:
            return IndexBarsResult(
                underlying=und,
                source="unavailable",
                data_gaps=["DATA_INSUFFICIENT: INDEX 1m chart empty/unparsed"],
            )
        last = getattr(bars[-1], "close", None)
        return IndexBarsResult(
            underlying=und,
            source="dhan_intraday_1m",
            bars=bars,
            bar_count=len(bars),
            last_close=float(last) if last is not None else None,
        )
    except Exception as exc:  # noqa: BLE001
        return IndexBarsResult(
            underlying=und,
            source="unavailable",
            data_gaps=[f"DATA_INSUFFICIENT: INDEX 1m {type(exc).__name__}"],
        )
