"""Read-only 'Background test (not traded)' route.

Serves data/research/background_test/<YYYY-MM-DD>.json written by the research box. This module deliberately
imports nothing from the desk P&L path (ui_feed history_rows / day_summaries / account, paper board,
paper_booked, model logs) and never writes anything. The rows are paper research only: never desk P&L.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException

REPO = Path(__file__).resolve().parents[4]
DATA_DIR = REPO / "data" / "research" / "background_test"
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
IST = timezone(timedelta(hours=5, minutes=30))

router = APIRouter()


def today_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d")


def load_day(day: str, data_dir: Optional[Path] = None) -> dict[str, Any]:
    """The day's JSON, or {"ok": False, "status": "NO_DATA"}. `day` must already be validated."""
    base = (data_dir or DATA_DIR).resolve()
    path = (base / f"{day}.json").resolve()
    if path.parent != base or not path.is_file():
        return {"ok": False, "status": "NO_DATA", "day": day}
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"ok": False, "status": "BAD_FILE", "day": day}
    if not isinstance(body, dict):
        return {"ok": False, "status": "BAD_FILE", "day": day}
    # whatever the file says, this is never desk P&L
    return {**body, "ok": True, "in_desk_pnl": False, "paper_only": True}


@router.get("/research/background-test")
def background_test(day: Optional[str] = None) -> dict[str, Any]:  # noqa: UP045 — FastAPI evals params on 3.9
    """Background test rows for one IST day (default today). Read-only; not in desk P&L."""
    d = day or today_ist()
    if not DAY_RE.match(d):
        raise HTTPException(status_code=422, detail="day must be YYYY-MM-DD")
    try:
        datetime.strptime(d, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="day must be a real date") from exc
    return load_day(d)
