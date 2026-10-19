"""Read-only 'Lab shadow trades' route.

Serves data/recon/lab_shadow/<YYYY-MM-DD>/events.csv, which the quant lead copies in from the research box
about every 30 min. This module deliberately imports nothing from the desk P&L path (ui_feed, desk_merge,
paper board, paper_booked, paper_extra, model logs) and never writes anything. Lab shadow rows are research
paper only: never desk paper, never desk P&L, never paper-extra.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException

REPO = Path(__file__).resolve().parents[4]
DATA_DIR = REPO / "data" / "recon" / "lab_shadow"
FILE_NAME = "events.csv"
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
IST = timezone(timedelta(hours=5, minutes=30))
MAX_BYTES = 5 * 1024 * 1024  # a day's lab feed is a few KB; refuse anything absurd

# seen_ist / sig / entry / exit are bare IST "HH:MM" in the real feed (full "YYYY-MM-DD HH:MM" also accepted);
# kept as text. rand15 = random-entry baseline (net ₹ at 1.5x), never filled in when empty.
COLUMNS = ("seen_ist", "lag_min", "strategy", "family", "status", "und", "side", "strike", "sig", "entry",
           "exit", "ask_in", "bid_out", "net15", "rand15", "data_gap", "situation", "reason", "src")
NUMERIC = ("lag_min", "strike", "ask_in", "bid_out", "net15", "rand15")
# v2 feed (from 2026-10-19 evening): trade_id = und_side_strike_entry_rule of the BASE trade (overlay rows carry their
# base's id) and cmp_kind = random_entry / random_exit / base / base_or_random / none. Optional: v1 files lack them.
OPTIONAL = ("trade_id", "cmp_kind")

router = APIRouter()


def today_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d")


def _num(v: Optional[str]) -> Optional[float]:
    if v is None:
        return None
    s = v.strip().replace(",", "")
    if not s:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    return f if f == f and f not in (float("inf"), float("-inf")) else None


def _txt(v: Optional[str]) -> Optional[str]:
    s = (v or "").strip()
    return s or None


def parse_csv(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    rows, missing, _fmt = parse_csv_fmt(text)
    return rows, missing


def parse_csv_fmt(text: str) -> tuple[list[dict[str, Any]], list[str], str]:
    """Rows (known columns only; '' -> None; numbers parsed) and the list of expected columns the file lacks.
    Lines starting with '#' are comments (used to mark test fixtures)."""
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    header = [h.strip() for h in (reader.fieldnames or [])]
    reader.fieldnames = header
    missing = [c for c in COLUMNS if c not in header]
    fmt = "v2" if all(c in header for c in OPTIONAL) else "v1"
    wanted = COLUMNS + tuple(c for c in OPTIONAL if c in header)
    rows: list[dict[str, Any]] = []
    for raw in reader:
        row: dict[str, Any] = {}
        for c in wanted:
            v = raw.get(c)
            row[c] = _num(v) if c in NUMERIC else _txt(v)
        if row["status"]:
            row["status"] = row["status"].upper()
        if row["side"]:
            row["side"] = row["side"].upper()
        if row.get("cmp_kind"):
            row["cmp_kind"] = row["cmp_kind"].lower()
        rows.append(row)
    return rows, missing, fmt


def load_day(day: str, data_dir: Optional[Path] = None) -> dict[str, Any]:
    """The day's rows, or {"ok": False, "status": "NO_DATA"}. `day` must already be validated."""
    base = (data_dir or DATA_DIR).resolve()
    path = (base / day / FILE_NAME).resolve()
    if path.parent.parent != base or path.parent.name != day or not path.is_file():
        return {"ok": False, "status": "NO_DATA", "day": day}
    try:
        st = path.stat()
        if st.st_size > MAX_BYTES:
            return {"ok": False, "status": "BAD_FILE", "day": day}
        rows, missing, fmt = parse_csv_fmt(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, csv.Error):
        return {"ok": False, "status": "BAD_FILE", "day": day}
    updated = datetime.fromtimestamp(st.st_mtime, IST).strftime("%Y-%m-%dT%H:%M:%S+05:30")
    return {
        "ok": True, "status": "OK", "day": day, "source": "lab-shadow",
        "label": "Lab shadow — not desk paper, ~20 min delayed",
        "paper_only": True, "in_desk_pnl": False, "in_paper_extra": False,
        "file_updated_ist": updated, "missing_columns": missing, "format": fmt, "rows": rows,
    }


@router.get("/research/lab-shadow")
def lab_shadow(day: Optional[str] = None) -> dict[str, Any]:  # noqa: UP045 — FastAPI evals params on 3.9
    """Lab shadow rows for one IST day (default today). Read-only; not desk paper, not in desk P&L."""
    d = day or today_ist()
    if not DAY_RE.match(d):
        raise HTTPException(status_code=422, detail="day must be YYYY-MM-DD")
    try:
        datetime.strptime(d, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="day must be a real date") from exc
    return load_day(d)
