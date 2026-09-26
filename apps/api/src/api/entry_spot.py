"""Read-only: index spot at entry for paper trades, looked up in the recorded dual tape.

Trades on the paper board carry no ``spot_at_entry``. The dual tape
(``data/recon/paper_watch/DUAL-TAPE/<day>.jsonl``) already recorded ``index_ltp`` per
underlying on every tick, so the spot at entry is the last tape print at or before
``opened_ts``. Never writes files, never touches the engine, never calls a broker.
"""

from __future__ import annotations

import json
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

IST = timezone(timedelta(hours=5, minutes=30))
MAX_GAP_S = 180
TRADE_KEYS = ("closed_trades", "open_trades", "tickets", "closed_trades_sample")

# path -> {"offset": bytes read, "series": {UND: ([ts...], [idx...])}}
_CACHE: dict[str, dict[str, Any]] = {}


def _ts(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        val = float(raw)
        return int(val / 1000 if val > 1e12 else val)
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return int((dt if dt.tzinfo else dt.replace(tzinfo=IST)).timestamp())


def _series(path: Path) -> dict[str, tuple[list[int], list[float]]]:
    """Parse the tape once, then only the bytes appended since the last call."""
    key = str(path)
    try:
        size = path.stat().st_size
    except OSError:
        return {}
    entry = _CACHE.get(key)
    if entry is None or size < entry["offset"]:
        entry = _CACHE[key] = {"offset": 0, "series": {}}
    if size > entry["offset"]:
        with path.open("rb") as fh:
            fh.seek(entry["offset"])
            chunk = fh.read(size - entry["offset"])
        end = chunk.rfind(b"\n") + 1  # keep a half-written last line for next time
        entry["offset"] += end
        for line in chunk[:end].splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict):
                continue
            row_ts = _ts(row.get("as_of_ist"))
            for snap in row.get("underlyings") or []:
                if not isinstance(snap, dict):
                    continue
                try:
                    idx = float(snap["index_ltp"])
                except (KeyError, TypeError, ValueError):
                    continue
                ts = _ts(snap.get("as_of_ist")) or row_ts
                if ts is None:
                    continue
                tss, idxs = entry["series"].setdefault(str(snap.get("underlying") or "").upper(), ([], []))
                i = bisect_right(tss, ts)
                tss.insert(i, ts)
                idxs.insert(i, idx)
    return entry["series"]


def spot_at(tape_dir: Path, underlying: str, opened_ts: Any) -> Optional[float]:
    ts = _ts(opened_ts)
    if ts is None or not underlying:
        return None
    day = datetime.fromtimestamp(ts, IST).date().isoformat()
    tss, idxs = _series(tape_dir / f"{day}.jsonl").get(str(underlying).upper(), ([], []))
    i = bisect_right(tss, ts) - 1
    if i < 0 or ts - tss[i] > MAX_GAP_S:
        return None
    return idxs[i]


def attach_entry_spots(blob: dict[str, Any], tape_dir: Path) -> dict[str, Any]:
    """Fill missing ``spot_at_entry`` in place from the tape. Leaves recorded values alone."""
    if not tape_dir.is_dir():
        return blob
    for key in TRADE_KEYS:
        for t in blob.get(key) or []:
            if not isinstance(t, dict) or t.get("spot_at_entry") is not None:
                continue
            spot = spot_at(tape_dir, t.get("underlying"), t.get("opened_ts") or t.get("opened_ist"))
            if spot is not None:
                t["spot_at_entry"] = spot
                t["spot_at_entry_src"] = "DUAL-TAPE"
    return blob
