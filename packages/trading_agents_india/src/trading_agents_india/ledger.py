"""Paper ledger: trading_agents_india.sqlite + data/recon/paper_watch/ JSONL.

Never touches transcripts.sqlite. No orders.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from trading_agents_india.session_clock import IST, now_ist

# Dual-tape / paper JSONL retention. 15m of 10s ticks ≈ 90 lines.
JSONL_KEEP_SECONDS = 15 * 60
JSONL_KEEP_FALLBACK_LINES = 90

PAPER_WATCH_MIXES = (
    "MIX-DEFAULT-BUY",
    "MIX-TA-FLOW-RISK",
    "MIX-TA-EVENT-HOLD",
    "MIX-TA-EXEC-SANITY",
    "MIX-TA-MARKET-HOURS",
    "MIX-LEAN-SPOT-ATM",
    "MIX-IMPULSE-1M",
    "MIX-PCR-EXTREME-HOLD",
    "MIX-003-INDEX-PROXY",
    "MIX-006-INDEX-PROXY",
    "MIX-SELL-CREDIT-PARK",
    "MIX-DUAL-INDEX-MASTER",
)


def paper_watch_root(repo_root: Path) -> Path:
    path = repo_root / "data" / "recon" / "paper_watch"
    path.mkdir(parents=True, exist_ok=True)
    return path


def jsonl_row_unix(row: dict[str, Any]) -> Optional[int]:
    raw: Any = row.get("as_of_ist")
    if raw is None and isinstance(row.get("clock"), dict):
        raw = row["clock"].get("as_of_ist")
    if raw is None:
        raw = row.get("ts_ist") or row.get("ts")
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        val = float(raw)
        if val > 1e12:
            val = val / 1000.0
        if val > 1e9:
            return int(val)
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return int(dt.timestamp())


def keep_jsonl_last_seconds(
    path: Path,
    *,
    seconds: int = JSONL_KEEP_SECONDS,
    now_ts: Optional[int] = None,
) -> dict[str, Any]:
    """Rewrite JSONL to rows in the last `seconds`. Does not invent ticks."""
    if not path.is_file():
        return {"ok": True, "kept": 0, "dropped": 0, "path": str(path), "reason": "missing"}
    lines = path.read_text(encoding="utf-8").splitlines()
    parsed: list[tuple[Optional[int], str]] = []
    for line in lines:
        text = line.strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        parsed.append((jsonl_row_unix(row), text))
    if not parsed:
        return {"ok": True, "kept": 0, "dropped": 0, "path": str(path), "reason": "empty"}
    stamped = [(ts, text) for ts, text in parsed if ts is not None]
    if now_ts is None:
        if stamped:
            now_ts = max(int(ts) for ts, _text in stamped)
        else:
            now_ts = int(datetime.now(IST).timestamp())
    cutoff = int(now_ts) - int(seconds)
    if stamped:
        kept_texts = [text for ts, text in stamped if int(ts) >= cutoff]
        dropped = len(stamped) - len(kept_texts)
        unstamped = len(parsed) - len(stamped)
        dropped += unstamped
    else:
        kept_texts = [text for _ts, text in parsed[-JSONL_KEEP_FALLBACK_LINES:]]
        dropped = max(0, len(parsed) - len(kept_texts))
    path.write_text(("\n".join(kept_texts) + ("\n" if kept_texts else "")), encoding="utf-8")
    return {
        "ok": True,
        "kept": len(kept_texts),
        "dropped": dropped,
        "path": str(path),
        "keep_seconds": int(seconds),
        "layer": "HYPOTHESIS",
    }


def append_jsonl(path: Path, row: dict[str, Any], *, trim_seconds: Optional[int] = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str, ensure_ascii=False) + "\n")
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass
    if trim_seconds is not None:
        keep_jsonl_last_seconds(path, seconds=int(trim_seconds))
    return path


def append_agent_paper_tick(
    repo_root: Path,
    *,
    session_payload: dict[str, Any],
    tick_index: int,
    clock: dict[str, Any],
    mixes: Optional[tuple[str, ...]] = None,
) -> list[Path]:
    """Append one tick to MIX-TA-* + MIX-DEFAULT-BUY paper_watch ledgers."""
    mixes = mixes or PAPER_WATCH_MIXES
    day = now_ist().date().isoformat()
    written: list[Path] = []
    base_event = {
        "source": "trading_agents_india",
        "tick_index": tick_index,
        "clock": clock,
        "mode": session_payload.get("mode", "PAPER"),
        "as_of_ist": session_payload.get("as_of_ist")
        or datetime.now(IST).isoformat(timespec="seconds"),
        "tickets": session_payload.get("tickets") or [],
        "handoffs_count": len(session_payload.get("handoffs") or []),
        "orders": "refused",
        "promote": False,
        "validated": False,
        "layer": "HYPOTHESIS",
        "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
        "data_gaps": session_payload.get("data_gaps") or [],
    }
    root = paper_watch_root(repo_root)
    for mix_id in mixes:
        path = root / mix_id / f"{day}.jsonl"
        row = {**base_event, "mix_id": mix_id}
        written.append(append_jsonl(path, row))
    return written


def try_backtest_paper_watch(mix_id: str, event: dict[str, Any]) -> Optional[str]:
    """Optional bridge to backtest_engine.paper_watch when package is installed."""
    try:
        from backtest_engine.paper_watch import append_paper_event  # type: ignore

        path = append_paper_event(mix_id, event)
        return str(path)
    except Exception:
        return None
