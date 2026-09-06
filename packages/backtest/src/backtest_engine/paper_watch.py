"""Append-only paper-watch ledger. No orders. Not a promote."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dhan_client.config import repo_root

IST = timezone(timedelta(hours=5, minutes=30))


def paper_watch_dir(mix_id: str) -> Path:
    path = repo_root() / "data" / "recon" / "paper_watch" / mix_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def append_paper_event(mix_id: str, event: dict[str, Any]) -> Path:
    """One JSON line per lean change / session tick of interest."""
    day = datetime.now(IST).date().isoformat()
    path = paper_watch_dir(mix_id) / f"{day}.jsonl"
    row = {
        "as_of_ist": datetime.now(IST).isoformat(),
        "mix_id": mix_id,
        "orders": "refused",
        "promote": False,
        "validated": False,
        **event,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")
    return path
