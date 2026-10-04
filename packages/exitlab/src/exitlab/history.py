"""1-minute NIFTY option + index parquet. Optional pyarrow (not a CI hard dep)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from exitlab.clock import IST
from exitlab.types import Bar

SESSION_OPEN = (9, 15)
SESSION_CLOSE = (15, 30)


class HistoryUnavailable(RuntimeError):
    """Parquet reader missing or file absent. Not a fabricated series."""


def _require_pyarrow() -> Any:
    try:
        import pyarrow.parquet as pq  # type: ignore[import-not-found,import-untyped,unused-ignore]
    except ImportError as exc:
        raise HistoryUnavailable(
            "pyarrow is required for --history parquet. Tests use synthetic bars."
        ) from exc
    return pq


def load_index_1m(path: Path, *, since: str | None = None, until: str | None = None) -> list[Bar]:
    pq = _require_pyarrow()
    table = pq.read_table(path)
    names = set(table.column_names)
    if "timestamp" in names:
        ts_col, o, h, low_c, c, v = "timestamp", "open", "high", "low", "close", "volume"
    elif "Datetime" in names:
        ts_col, o, h, low_c, c, v = "Datetime", "Open", "High", "Low", "Close", "Volume"
    else:
        raise HistoryUnavailable(f"{path}: no timestamp column {sorted(names)}")
    cols = {n: table.column(n).to_pylist() for n in (ts_col, o, h, low_c, c) if n in names}
    vols = table.column(v).to_pylist() if v in names else [None] * len(cols[ts_col])
    out: list[Bar] = []
    for i, raw_ts in enumerate(cols[ts_col]):
        ts = _as_bar_ts(raw_ts)
        if ts is None:
            continue
        day = ts.date().isoformat()
        if since and day < since:
            continue
        if until and day > until:
            continue
        if not _session_minute(ts):
            continue
        close = float(cols[c][i])
        # Bar is known at its own close stamp (1m close).
        out.append(
            Bar(
                ts=ts,
                available_ts=ts,
                open=float(cols[o][i]),
                high=float(cols[h][i]),
                low=float(cols[low_c][i]),
                close=close,
                volume=_opt_float(vols[i]),
                index_open=float(cols[o][i]),
                index_high=float(cols[h][i]),
                index_low=float(cols[low_c][i]),
                index_close=close,
            )
        )
    out.sort(key=lambda b: b.available_ts)
    return out


def load_option_week(path: Path) -> list[Bar]:
    pq = _require_pyarrow()
    table = pq.read_table(path)
    n = table.num_rows
    ts = table.column("timestamp").to_pylist()
    o = table.column("open").to_pylist()
    h = table.column("high").to_pylist()
    lo = table.column("low").to_pylist()
    c = table.column("close").to_pylist()
    vol = table.column("volume").to_pylist()
    oi = table.column("open_interest").to_pylist()
    strike = table.column("strike").to_pylist()
    side = table.column("option_type").to_pylist()
    out: list[Bar] = []
    for i in range(n):
        stamp = _as_bar_ts(ts[i])
        if stamp is None or not _session_minute(stamp):
            continue
        close = float(c[i])
        out.append(
            Bar(
                ts=stamp,
                available_ts=stamp,
                open=float(o[i]),
                high=float(h[i]),
                low=float(lo[i]),
                close=close,
                volume=_opt_float(vol[i]),
                oi=_opt_float(oi[i]),
                strike=float(strike[i]),
                side=str(side[i]).upper(),
            )
        )
    out.sort(key=lambda b: (b.available_ts, b.strike or 0.0, b.side or ""))
    return out


def option_path(
    bars: list[Bar],
    *,
    side: str,
    strike: float,
    session: str,
) -> list[Bar]:
    """Bars for one contract on one IST calendar day. Empty if missing (do not fabricate)."""
    want = side.upper()
    return [
        b
        for b in bars
        if b.side == want
        and b.strike is not None
        and abs(float(b.strike) - float(strike)) < 1e-6
        and b.ts.astimezone(IST).date().isoformat() == session
    ]


def index_on_session(index: list[Bar], session: str) -> list[Bar]:
    return [b for b in index if b.ts.astimezone(IST).date().isoformat() == session]


def _as_bar_ts(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        dt = raw
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        return dt.astimezone(IST)
    return None


def _session_minute(ts: datetime) -> bool:
    t = ts.astimezone(IST).time()
    start = timedelta(hours=SESSION_OPEN[0], minutes=SESSION_OPEN[1])
    end = timedelta(hours=SESSION_CLOSE[0], minutes=SESSION_CLOSE[1])
    now = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
    return start <= now < end


def _opt_float(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def last3d_dir(data: Path) -> Path | None:
    """Prefer `.local_data/last3d/`, else parquet sitting next to `--data`."""
    for cand in (data / "last3d", data):
        idx = cand / "index_last3d.parquet"
        parts = list(cand.glob("opt1m_last3d_part*.parquet"))
        if idx.is_file() and parts:
            return cand
    return None


def load_last3d_index(path: Path) -> dict[str, list[Bar]]:
    """1m NIFTY index grouped by `trading_day`. Small enough to keep in RAM."""
    pq = _require_pyarrow()
    table = pq.read_table(path)
    names = set(table.column_names)
    if "timestamp" not in names or "close" not in names:
        raise HistoryUnavailable(f"{path}: need timestamp+close, got {sorted(names)}")
    ts = table.column("timestamp").to_pylist()
    o = table.column("open").to_pylist() if "open" in names else None
    h = table.column("high").to_pylist() if "high" in names else None
    lo = table.column("low").to_pylist() if "low" in names else None
    c = table.column("close").to_pylist()
    vol = table.column("volume").to_pylist() if "volume" in names else None
    days = table.column("trading_day").to_pylist() if "trading_day" in names else None
    by: dict[str, list[Bar]] = defaultdict(list)
    for i, raw_ts in enumerate(ts):
        stamp = _as_bar_ts(raw_ts)
        if stamp is None or not _session_minute(stamp):
            continue
        day = str(days[i]) if days is not None else stamp.date().isoformat()
        close = float(c[i])
        open_px = float(o[i]) if o is not None else close
        high_px = float(h[i]) if h is not None else close
        low_px = float(lo[i]) if lo is not None else close
        by[day].append(
            Bar(
                ts=stamp,
                available_ts=stamp,
                open=open_px,
                high=high_px,
                low=low_px,
                close=close,
                volume=_opt_float(vol[i]) if vol is not None else None,
                index_open=open_px,
                index_high=high_px,
                index_low=low_px,
                index_close=close,
            )
        )
    for day in by:
        by[day].sort(key=lambda b: b.available_ts)
    return dict(by)


def iter_last3d_days(data: Path) -> Iterator[tuple[str, list[Bar], list[Bar], str]]:
    """Yield `(session, opt_bars, index_bars, expiry)` one day at a time.

    Option last-3d files have no `open` column — `Bar.open` is the close.
    Parts are disjoint by day; each part is scanned once and discarded.
    """
    root = last3d_dir(data)
    if root is None:
        raise HistoryUnavailable(f"{data}: no last3d index + opt1m_last3d_part*.parquet")
    by_idx = load_last3d_index(root / "index_last3d.parquet")
    pq = _require_pyarrow()
    for path in sorted(root.glob("opt1m_last3d_part*.parquet")):
        table = pq.read_table(path)
        names = set(table.column_names)
        need = {"timestamp", "high", "low", "close", "strike", "option_type"}
        if not need.issubset(names):
            raise HistoryUnavailable(f"{path}: missing {sorted(need - names)}")
        ts = table.column("timestamp").to_pylist()
        h = table.column("high").to_pylist()
        lo = table.column("low").to_pylist()
        c = table.column("close").to_pylist()
        vol = table.column("volume").to_pylist() if "volume" in names else None
        oi = table.column("open_interest").to_pylist() if "open_interest" in names else None
        strike = table.column("strike").to_pylist()
        side = table.column("option_type").to_pylist()
        day_col = table.column("trading_day").to_pylist() if "trading_day" in names else None
        exp_col = table.column("expiry").to_pylist() if "expiry" in names else None
        n = table.num_rows
        del table
        by_day: dict[str, list[int]] = defaultdict(list)
        for i in range(n):
            if day_col is not None:
                day = str(day_col[i])
            else:
                stamp = _as_bar_ts(ts[i])
                if stamp is None:
                    continue
                day = stamp.date().isoformat()
            by_day[day].append(i)
        for day, idxs in by_day.items():
            expiry = str(exp_col[idxs[0]]) if exp_col is not None else day
            bars: list[Bar] = []
            for i in idxs:
                stamp = _as_bar_ts(ts[i])
                if stamp is None or not _session_minute(stamp):
                    continue
                close = float(c[i])
                bars.append(
                    Bar(
                        ts=stamp,
                        available_ts=stamp,
                        open=close,
                        high=float(h[i]),
                        low=float(lo[i]),
                        close=close,
                        volume=_opt_float(vol[i]) if vol is not None else None,
                        oi=_opt_float(oi[i]) if oi is not None else None,
                        strike=float(strike[i]),
                        side=str(side[i]).upper(),
                    )
                )
            bars.sort(key=lambda b: (b.available_ts, b.strike or 0.0, b.side or ""))
            yield day, bars, by_idx.get(day) or [], expiry
