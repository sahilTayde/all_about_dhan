"""Read-only 'PX exit labels + shadow exits' route for the desk page (DESK_PAGE_SPEC.md, 2026-10-19 shadow overlays bundle).

Reads, never writes, the paper-extra runner's display-only outputs straight from disk:
  data/recon/paper_extra/<day>.json                      rows[] (PX rows: exit_status, shadow_overlays, regime, shadow_narrow_open)
  data/paper_extra/<day>/live_exits_status.json          [{key:[rule_id, und, signal_time], exit_status}]  (3 s refresh)
  data/paper_extra/<day>/live_exits.json                 live pricer state (entry, S, hw, stop_floor, trail_gap) -> live stop
  data/recon/paper_extra/shadow_overlays_<day>.jsonl     one line per closed PX trade (actual / base60_1m / t50 / ts / DR)
  data/recon/paper_extra/shadow_narrow_open_<day>.jsonl  one line per closed trade (narrow-open rule shadow)
Chosen instead of widening research_rules.paper_extra_rows: that function books trades and feeds desk totals; keeping it
untouched means no shadow number can ever reach the desk / paper-extra P&L. This module imports nothing from ui_feed,
desk_merge, research_rules or the runner. Missing file -> that part is reported missing, never an error.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException

REPO = Path(__file__).resolve().parents[4]
RECON_DIR = REPO / "data" / "recon" / "paper_extra"
LIVE_DIR = REPO / "data" / "paper_extra"
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
IST = timezone(timedelta(hours=5, minutes=30))
MAX_BYTES = 20 * 1024 * 1024

# display fields copied per PX row (nothing else from the row is passed on)
ROW_FIELDS = ("rule_id", "strategy", "underlying", "side", "strike", "signal_time", "entry_time", "entry_px", "status",
              "stop_px", "target_px", "trail", "exit_time", "exit_px", "exit_reason", "mark_px", "mark_time")
SHADOW_FIELDS = ("exit_status", "shadow_overlays", "regime", "shadow_narrow_open")

router = APIRouter()


def today_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d")


def _fin(x: Any) -> Optional[float]:
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _inside(base: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _read_json(base: Path, path: Path) -> tuple[str, Any]:
    if not _inside(base, path) or not path.is_file():
        return "missing", None
    try:
        if path.stat().st_size > MAX_BYTES:
            return "bad", None
        return "ok", json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "bad", None


def _read_jsonl(base: Path, path: Path) -> tuple[str, list, int]:
    if not _inside(base, path) or not path.is_file():
        return "missing", [], 0
    try:
        if path.stat().st_size > MAX_BYTES:
            return "bad", [], 0
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "bad", [], 0
    out, bad = [], 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if isinstance(obj, dict):
            out.append(obj)
        else:
            bad += 1
    return "ok", out, bad


def _key(rule_id: Any, und: Any, sig: Any) -> Optional[str]:
    if not rule_id or not sig:
        return None
    return f"{rule_id}|{und or 'NIFTY'}|{sig}"


def live_stop(t: dict) -> Optional[dict]:
    """Live stop exactly as scripts/paper_extra/live_pricer.LiveTrade.stop computes it, from the pricer's saved state.
    None when entry / S / hw are missing (never guessed)."""
    entry, s_frac, hw = _fin(t.get("entry")), _fin(t.get("S")), _fin(t.get("hw"))
    if entry is None or s_frac is None or hw is None:
        return None
    hw = max(hw, entry)
    base = entry * (1 - s_frac)
    stop, which = base, "base stop"
    armed = hw >= entry * (1 + s_frac)
    be_trail = max(entry, hw * (1 - s_frac)) if armed else None
    if be_trail is not None and be_trail > stop:
        stop, which = be_trail, "BE trail"
    floor = _fin(t.get("stop_floor")) or None  # pricer: `if self.stop_floor:` (0 / None = off)
    if floor is not None and floor > stop:
        stop, which = floor, "stop floor"
    gap = _fin(t.get("trail_gap")) or None
    gap_px = hw * (1 - gap) if gap is not None else None
    if gap_px is not None and gap_px > stop:
        stop, which = gap_px, "gap trail"
    return {"live_stop": round(stop, 2), "binding": which, "base_stop": round(base, 2), "hw": round(hw, 2),
            "trail_armed": armed, "be_trail": None if be_trail is None else round(be_trail, 2),
            "stop_floor": floor, "trail_gap": gap, "gap_trail": None if gap_px is None else round(gap_px, 2),
            "last_bid": _fin(t.get("last_bid")), "last_ts": t.get("last_ts"), "closed": t.get("closed")}


def load_day(day: str, recon_dir: Optional[Path] = None, live_dir: Optional[Path] = None) -> dict[str, Any]:
    """Everything the page needs for one day. `day` must already be validated."""
    recon, live = (recon_dir or RECON_DIR), (live_dir or LIVE_DIR)
    src: dict[str, str] = {}

    src["rows"], blob = _read_json(recon, recon / f"{day}.json")
    rows = []
    if isinstance(blob, dict) and blob.get("day") == day:
        for r in blob.get("rows") or []:
            if not isinstance(r, dict) or not str(r.get("rule_id", "")).startswith("PX_"):
                continue
            out = {k: r.get(k) for k in ROW_FIELDS}
            out.update({k: r[k] for k in SHADOW_FIELDS if k in r})
            out["key"] = _key(r.get("rule_id"), r.get("underlying"), r.get("signal_time"))
            rows.append(out)
    elif src["rows"] == "ok":
        src["rows"] = "other_day"

    src["live_status"], side = _read_json(live, live / day / "live_exits_status.json")
    status_by_key = {}
    for x in side if isinstance(side, list) else []:
        k = x.get("key") if isinstance(x, dict) else None
        if isinstance(k, list) and len(k) == 3 and isinstance(x.get("exit_status"), dict):
            status_by_key[_key(*k)] = x["exit_status"]

    src["live_exits"], lx = _read_json(live, live / day / "live_exits.json")
    live_by_key = {}
    for t in lx if isinstance(lx, list) else []:
        k = t.get("key") if isinstance(t, dict) else None
        if isinstance(k, list) and len(k) == 3:
            live_by_key[_key(*k)] = live_stop(t)

    src["shadow_overlays"], so_lines, so_bad = _read_jsonl(recon, recon / f"shadow_overlays_{day}.jsonl")
    src["shadow_narrow_open"], no_lines, no_bad = _read_jsonl(recon, recon / f"shadow_narrow_open_{day}.jsonl")

    for r in rows:  # fresher sidecar status wins for OPEN rows; closed rows never carry a label
        if r.get("status") == "OPEN" and r["key"] in status_by_key:
            r["exit_status"] = status_by_key[r["key"]]
            r["exit_status_src"] = "live_exits_status.json"
        elif r.get("exit_status") is not None:
            r["exit_status_src"] = f"{day}.json"
        r["live"] = live_by_key.get(r["key"]) if r.get("status") == "OPEN" else None

    return {
        "ok": True, "day": day, "display_only": True, "shadow_only": True, "in_desk_pnl": False, "in_paper_extra_total": False,
        "sources": src, "bad_lines": {"shadow_overlays": so_bad, "shadow_narrow_open": no_bad},
        "rows": rows, "live_by_key": {k: v for k, v in live_by_key.items() if v is not None},
        "status_by_key": status_by_key, "shadow_overlays": so_lines, "shadow_narrow_open": no_lines,
    }


@router.get("/research/px-exits")
def px_exits(day: Optional[str] = None) -> dict[str, Any]:  # noqa: UP045 — FastAPI evals params on 3.9
    """PX exit labels + shadow exits for one IST day (default today). Read-only; display only; never in any total."""
    d = day or today_ist()
    if not DAY_RE.match(d):
        raise HTTPException(status_code=422, detail="day must be YYYY-MM-DD")
    try:
        datetime.strptime(d, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="day must be a real date") from exc
    return load_day(d)
