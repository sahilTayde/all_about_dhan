"""Recorder health: last-frame age. Record only; no orders."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from marketdata.clock import IST

STATUS_NAME = "recorder_status.json"
STALE_AFTER_S = 60.0


def status_path(day_dir: Path) -> Path:
    return Path(day_dir) / STATUS_NAME


def write_status(
    day_dir: Path,
    *,
    last_frame_ts: str | None,
    last_frame_unix: float | None,
    frames: int,
    connected: bool,
) -> Path:
    path = status_path(day_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    row: dict[str, Any] = {
        "last_frame_ts": last_frame_ts,
        "last_frame_unix": last_frame_unix,
        "frames": int(frames),
        "connected": bool(connected),
        "stale_after_s": STALE_AFTER_S,
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    return path


def read_status(day_dir: Path) -> dict[str, Any] | None:
    path = status_path(day_dir)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def assess_health(
    day_dir: Path,
    *,
    now: float | None = None,
    stale_after_s: float = STALE_AFTER_S,
    process_running: bool = True,
) -> dict[str, Any]:
    """HEALTHY only when the process is up and a frame arrived within ``stale_after_s``."""
    clock = float(now) if now is not None else datetime.now(IST).timestamp()
    row = read_status(day_dir)
    last = None
    frames = 0
    if row is not None:
        raw_last = row.get("last_frame_unix")
        if isinstance(raw_last, (int, float)):
            last = float(raw_last)
        frames = int(row.get("frames") or 0)
    if last is None:
        verdict = "UNHEALTHY"
        reason = "no frames recorded"
        age: float | None = None
    else:
        age = max(0.0, clock - last)
        if age > float(stale_after_s):
            verdict = "UNHEALTHY"
            reason = f"no frames in {int(age)}s"
        elif not process_running:
            verdict = "UNHEALTHY"
            reason = "process STOPPED"
        else:
            verdict = "HEALTHY"
            reason = f"last frame {int(age)}s ago"
    healthy = verdict == "HEALTHY"
    return {
        "healthy": healthy,
        "verdict": verdict,
        "reason": reason,
        "last_frame_unix": last,
        "last_frame_age_s": age,
        "frames": frames,
        "process_running": process_running,
        "line": f"{verdict} ({reason})",
    }
