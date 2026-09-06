"""Paper ledger: trading_agents_india.sqlite + data/recon/paper_watch/ JSONL.

Never touches transcripts.sqlite. No orders.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from trading_agents_india.session_clock import IST, now_ist

PAPER_WATCH_MIXES = (
    "MIX-DEFAULT-BUY",
    "MIX-TA-FLOW-RISK",
    "MIX-TA-EVENT-HOLD",
    "MIX-TA-EXEC-SANITY",
    "MIX-TA-MARKET-HOURS",
)


def paper_watch_root(repo_root: Path) -> Path:
    path = repo_root / "data" / "recon" / "paper_watch"
    path.mkdir(parents=True, exist_ok=True)
    return path


def append_jsonl(path: Path, row: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str, ensure_ascii=False) + "\n")
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
