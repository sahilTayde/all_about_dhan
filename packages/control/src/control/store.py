"""Idempotent founder-command store (memory + optional ledger table)."""

from __future__ import annotations

from typing import Any, Protocol, cast


class CommandStore(Protocol):
    def get(self, command_id: str) -> dict[str, Any] | None: ...

    def put_if_absent(self, row: dict[str, Any]) -> dict[str, Any]: ...

    def update_ack(
        self, command_id: str, status: str, status_reason: str | None, applied_ts: str | None
    ) -> dict[str, Any]: ...

    def all(self) -> list[dict[str, Any]]: ...


class MemoryCommandStore:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def get(self, command_id: str) -> dict[str, Any] | None:
        row = self.rows.get(command_id)
        return dict(row) if row is not None else None

    def put_if_absent(self, row: dict[str, Any]) -> dict[str, Any]:
        cid = str(row.get("command_id") or row["id"])
        if cid in self.rows:
            return dict(self.rows[cid])
        stored = dict(row)
        stored["command_id"] = cid
        stored["id"] = cid
        self.rows[cid] = stored
        return dict(stored)

    def update_ack(
        self, command_id: str, status: str, status_reason: str | None, applied_ts: str | None
    ) -> dict[str, Any]:
        row = self.rows.setdefault(command_id, {"command_id": command_id, "id": command_id})
        row["status"] = status
        row["status_reason"] = status_reason
        row["applied_ts"] = applied_ts
        return dict(row)

    def all(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.rows.values()]


class LedgerCommandStore:
    """Adapter over ledger.v2.SqliteLedgerStore.founder_commands."""

    def __init__(self, ledger: Any) -> None:
        self.ledger = ledger

    def get(self, command_id: str) -> dict[str, Any] | None:
        row = self.ledger.get_founder_command(command_id)
        return cast(dict[str, Any], dict(row)) if row is not None else None

    def put_if_absent(self, row: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], dict(self.ledger.record_founder_command(row)))

    def update_ack(
        self, command_id: str, status: str, status_reason: str | None, applied_ts: str | None
    ) -> dict[str, Any]:
        raw = self.ledger.ack_founder_command(command_id, status, status_reason, applied_ts)
        return cast(dict[str, Any], dict(raw))

    def all(self) -> list[dict[str, Any]]:
        return [cast(dict[str, Any], dict(r)) for r in self.ledger.list_founder_commands()]
