"""Isolated JSONL journal. Never sqlite. Never the legacy ledger."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from shadow.safety import ACCOUNT_ID, ShadowSafetyError, assert_isolated_state

SCHEMA = "shadow-v2"


@dataclass(frozen=True)
class DayFiles:
    day: str
    decisions: Path
    pnl: Path
    compare: Path
    status: Path


class ShadowJournal:
    """Append-only decision + P&L rows under an isolated state dir."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = assert_isolated_state(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def files(self, day: str) -> DayFiles:
        folder = self.state_dir / day
        folder.mkdir(parents=True, exist_ok=True)
        return DayFiles(
            day=day,
            decisions=folder / "decisions.jsonl",
            pnl=folder / "pnl.jsonl",
            compare=folder / "compare.json",
            status=folder / "status.json",
        )

    def append(self, path: Path, row: dict[str, Any]) -> None:
        if path.suffix not in {".jsonl", ".json"}:
            raise ShadowSafetyError(f"V2 shadow refuse write of {path.name}")
        assert_isolated_state(path.parent)
        line = json.dumps(row, separators=(",", ":"), sort_keys=True, allow_nan=False)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def write_json(self, path: Path, row: dict[str, Any]) -> None:
        assert_isolated_state(path.parent)
        path.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def log_decision(
        self,
        *,
        day: str,
        ts: str,
        underlying: str,
        action: str,
        side: str,
        reason: str,
        ltp: float | None,
        instrument_id: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "schema": SCHEMA,
            "kind": "DECISION",
            "account_id": ACCOUNT_ID,
            "day": day,
            "ts": ts,
            "underlying": underlying,
            "action": action,
            "side": side,
            "reason": reason,
            "ltp": ltp,
            "instrument_id": instrument_id,
            "orders": "REFUSED",
            "promote": False,
            "stage": "shadow",
        }
        if extra:
            row.update(extra)
        self.append(self.files(day).decisions, row)
        return row

    def log_pnl(
        self,
        *,
        day: str,
        ts: str,
        kind: str,
        instrument_id: str,
        qty: int,
        price: float | None,
        realized: float,
        reason: str,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "schema": SCHEMA,
            "kind": kind,
            "account_id": ACCOUNT_ID,
            "day": day,
            "ts": ts,
            "instrument_id": instrument_id,
            "qty": qty,
            "price": price,
            "realized_pts": realized,
            "reason": reason,
            "orders": "REFUSED",
        }
        self.append(self.files(day).pnl, row)
        return row

    def iter_jsonl(self, path: Path) -> Iterator[dict[str, Any]]:
        if not path.is_file():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj

    def write_status(self, day: str, clock_now: datetime, **fields: Any) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema": SCHEMA,
            "account_id": ACCOUNT_ID,
            "day": day,
            "ts": clock_now.isoformat(timespec="seconds"),
            "orders": "REFUSED",
            "promote": False,
            **fields,
        }
        self.write_json(self.files(day).status, body)
        return body
