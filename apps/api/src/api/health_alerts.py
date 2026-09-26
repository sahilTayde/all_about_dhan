"""Read-only founder health routes: files written by `python -m health` (packages/health)."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

HEALTH_DIR = Path(__file__).resolve().parents[4] / "data" / "health"

router = APIRouter(tags=["health"])


@router.get("/health/status")
def health_status() -> dict[str, Any]:
    try:
        return json.loads((HEALTH_DIR / "status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"ok": None, "checks": {}, "note": "health monitor has not run yet: python -m health --once"}


@router.get("/health/alerts")
def health_alerts(limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    try:
        with open(HEALTH_DIR / "alerts.jsonl", encoding="utf-8") as f:
            tail = deque(f, maxlen=limit)
    except OSError:
        tail = deque()
    alerts = []
    for line in reversed(tail):
        try:
            alerts.append(json.loads(line))
        except ValueError:
            continue
    return {"alerts": alerts, "count": len(alerts)}
