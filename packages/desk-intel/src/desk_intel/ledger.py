"""Paper + shadow P/L ledger. Never live orders. Execution remains refused."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from desk_intel.schema import LifecycleRecord, UserFill
from desk_intel.time_ist import now_ist, now_ist_iso


def ledger_day_path(root: Path, ledger_dir: str, day: Optional[str] = None) -> Path:
    stamp = day or now_ist().date().isoformat()
    return root / ledger_dir / stamp / "ledger.json"


def empty_ledger(day: str) -> dict[str, Any]:
    return {
        "day": day,
        "as_of_ist": now_ist_iso(),
        "note": "Paper + shadow ledger only. No live orders. Execution refused.",
        "users": {},
        "records": [],
    }


def load_ledger(root: Path, ledger_dir: str, day: Optional[str] = None) -> dict[str, Any]:
    path = ledger_day_path(root, ledger_dir, day)
    if not path.is_file():
        stamp = day or now_ist().date().isoformat()
        return empty_ledger(stamp)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        stamp = day or now_ist().date().isoformat()
        return empty_ledger(stamp)
    return raw


def save_ledger(root: Path, ledger_dir: str, payload: dict[str, Any], day: Optional[str] = None) -> Path:
    path = ledger_day_path(root, ledger_dir, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["as_of_ist"] = now_ist_iso()
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def record_user_fill(
    root: Path,
    ledger_dir: str,
    signal_id: str,
    fill: UserFill,
    day: Optional[str] = None,
) -> Path:
    payload = load_ledger(root, ledger_dir, day)
    payload.setdefault("users", {})
    payload["users"][signal_id] = fill.to_dict()
    return save_ledger(root, ledger_dir, payload, day)


def users_from_ledger(payload: dict[str, Any]) -> dict[str, UserFill]:
    out: dict[str, UserFill] = {}
    for key, raw in (payload.get("users") or {}).items():
        if not isinstance(raw, dict):
            continue
        out[str(key)] = UserFill(
            took_trade=bool(raw.get("took_trade")),
            lots=raw.get("lots"),
            spot=raw.get("spot"),
            reported_pnl=raw.get("reported_pnl"),
            recorded_at=str(raw.get("recorded_at") or ""),
        )
    return out


def upsert_records(payload: dict[str, Any], records: list[LifecycleRecord]) -> dict[str, Any]:
    payload["records"] = [r.to_dict() for r in records]
    payload["still_valid_forbidden_overnight"] = all(not r.still_valid for r in records)
    return payload
