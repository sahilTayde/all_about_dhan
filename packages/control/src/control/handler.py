"""Engine handler: persist, apply from available_ts, COMMAND_ACK. Never places an entry."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from contracts.clock import IST, LiveClock
from contracts.envelope import Envelope
from events.schema import Event

from control.kinds import (
    CONFIRM_KINDS,
    EXIT_KINDS,
    CommandBook,
    aware_ist,
    canonical_kind,
    make_row,
    ts_of,
    validate_args,
    validate_row,
)
from control.log import append_command, read_commands
from control.store import CommandStore, MemoryCommandStore

KILL_NAME = "KILL_SWITCH"


def _iso(now: datetime) -> str:
    return now.astimezone(IST).isoformat(timespec="seconds")


class ControlHandler:
    """Apply founder commands. Flatten/kill use the position manager + risk checks."""

    def __init__(
        self,
        *,
        store: CommandStore | None = None,
        root: Path | None = None,
        clock: Any | None = None,
        bus: Any | None = None,
        manager: Any | None = None,
        risk: Any | None = None,
        kill_switch_path: Path | None = None,
        ledger: Any | None = None,
    ) -> None:
        self.store: CommandStore = store if store is not None else MemoryCommandStore()
        self.root = Path(root) if root is not None else None
        self.clock = clock if clock is not None else LiveClock()
        self.bus = bus
        self.manager = manager
        self.risk = risk
        default_kill = (self.root / KILL_NAME) if self.root is not None else Path(KILL_NAME)
        self.kill_switch_path = Path(kill_switch_path) if kill_switch_path is not None else default_kill
        self.ledger = ledger
        self.last_ack: dict[str, Any] | None = None
        self.entry_orders: list[str] = []

    def book(self) -> CommandBook:
        if self.root is None:
            return CommandBook(self.store.all())
        loaded = read_commands(self.root)
        return CommandBook(loaded.rows, loaded.problems, loaded.blocked_from)

    def allows_entry(self, now: datetime | None = None, *, underlying: str = "", strategy_id: str = "") -> str | None:
        when = (now or self.clock.now()).astimezone(IST)
        return self.book().entry_reason(when.timestamp(), underlying=underlying, strategy_id=strategy_id)

    def on_bus_event(self, event: Event) -> dict[str, Any]:
        payload = dict(event.payload)
        payload.setdefault("available_ts", event.timestamp)
        return self.apply(payload)

    def handle(self, envelope: Envelope) -> dict[str, Any]:
        if envelope.event_type != "FOUNDER_COMMAND":
            return {"status": "ignored", "reason": envelope.event_type}
        payload = dict(envelope.payload)
        payload.setdefault("available_ts", envelope.available_ts)
        return self.apply(payload)

    def apply(self, raw: dict[str, Any]) -> dict[str, Any]:
        cid = str(raw.get("command_id") or raw.get("id") or "")
        existing = self.store.get(cid) if cid else None
        if existing is not None and existing.get("status") in {"applied", "rejected"}:
            self.last_ack = existing
            self._publish_ack(existing)
            return existing
        err = validate_row(raw) if cid else "bad command_id"
        if err:
            ack = self._ack(raw, "rejected", err)
            return ack
        available = aware_ist(str(raw.get("available_ts") or _iso(self.clock.now())))
        if available > self.clock.now().astimezone(IST):
            ack = self._ack(raw, "pending", "available_ts in the future")
            return ack
        row = make_row(
            str(raw["kind"]),
            dict(raw.get("args") or {}),
            actor=str(raw["actor"]),
            reason=str(raw["reason"]),
            available_ts=available,
            command_id=cid,
            source=str(raw.get("source") or "engine"),
        )
        stored = self.store.put_if_absent(row)
        already = stored.get("status") in {"applied", "rejected"} and stored.get("command_id") == cid
        if already and (stored.get("applied_ts") or stored.get("status") == "rejected"):
            self.last_ack = stored
            self._publish_ack(stored)
            return stored
        if self.root is not None:
            append_command(self.root, stored)
        if self.ledger is not None and hasattr(self.ledger, "record_founder_command"):
            self.ledger.record_founder_command(stored)
        ack = self._run(stored)
        return ack

    def _run(self, row: dict[str, Any]) -> dict[str, Any]:
        kind = canonical_kind(str(row["kind"]))
        before = self._entry_order_ids()
        try:
            if kind in EXIT_KINDS:
                detail = self._apply_exit(row)
            elif kind == "REARM":
                detail = self._rearm()
            else:
                when = float(ts_of(row.get("ts") or row.get("available_ts") or self.clock.now()))
                detail = {"state": self.book().state_at(when).as_dict(when)}
        except Exception as exc:
            return self._ack(row, "rejected", f"{type(exc).__name__}: {exc}")
        after = self._entry_order_ids()
        new_entries = [oid for oid in after if oid not in before]
        if new_entries:
            self.entry_orders.extend(new_entries)
            return self._ack(row, "rejected", "CONTROL_MUST_NOT_PLACE_ENTRY")
        extra = {"who": row["actor"], "when": row["available_ts"], "why": row["reason"]}
        extra.update(detail)
        return self._ack(row, "applied", None, extra)

    def _apply_exit(self, row: dict[str, Any]) -> dict[str, Any]:
        kind = canonical_kind(str(row["kind"]))
        now = self.clock.now()
        if self.risk is not None:
            rd = self.risk.check_flatten(now=now)
            if not getattr(rd, "approved", False):
                raise RuntimeError(getattr(rd, "reason_code", None) or getattr(rd, "reason", "RISK_VETO"))
        if kind == "KILL":
            self.kill_switch_path.parent.mkdir(parents=True, exist_ok=True)
            self.kill_switch_path.write_text("on\n", encoding="utf-8")
            if self.manager is not None:
                self.manager.kill_switch = True
        fired: list[str] = []
        if self.manager is not None:
            args = dict(row.get("args") or {})
            targets = self._targets(kind, args)
            if not targets and kind == "CUT_LOSS":
                raise RuntimeError("TRADE_NOT_OPEN: no open ticket with this id")
            if not targets:
                iso = _iso(now)
                env = Envelope(
                    v=2,
                    event_type="FOUNDER_COMMAND",
                    event_id=str(row["command_id"]),
                    stream="ctl:commands",
                    source="control",
                    event_ts=iso,
                    available_ts=iso,
                    timestamp=iso,
                    account_id="founder",
                    correlation_id=str(row["command_id"]),
                    causation_id=None,
                    payload={"kind": kind, **args},
                )
                for req in self.manager.on_market(env):
                    fired.append(req.reason)
            else:
                for pos in targets:
                    iso = _iso(now)
                    env = Envelope(
                        v=2,
                        event_type="FOUNDER_COMMAND",
                        event_id=str(row["command_id"]),
                        stream="ctl:commands",
                        source="control",
                        event_ts=iso,
                        available_ts=iso,
                        timestamp=iso,
                        account_id=str(pos.get("account_id") or "founder"),
                        correlation_id=str(row["command_id"]),
                        causation_id=None,
                        payload={
                            "kind": kind,
                            "instrument_id": pos.get("instrument_id"),
                            "position_id": pos.get("position_id"),
                        },
                    )
                    for req in self.manager.on_market(env):
                        fired.append(req.reason)
        return {"exits": fired, "kind": kind}

    def _targets(self, kind: str, args: dict[str, Any]) -> list[dict[str, Any]]:
        if self.manager is None:
            return []
        open_pos = list(self.manager.store.open_positions())
        if kind == "CUT_LOSS":
            tid = str(args.get("position_id") or args.get("trade_id") or args.get("instrument_id") or "")
            return [
                p
                for p in open_pos
                if tid
                in {
                    str(p.get("position_id") or ""),
                    str(p.get("instrument_id") or ""),
                    str(p.get("symbol") or ""),
                }
            ]
        if kind == "FLATTEN_ALL" and args.get("underlying"):
            und = str(args["underlying"]).upper()
            return [p for p in open_pos if und in str(p.get("instrument_id") or "").upper()]
        return []

    def _rearm(self) -> dict[str, Any]:
        if self.kill_switch_path.exists():
            self.kill_switch_path.unlink()
        if self.manager is not None:
            self.manager.kill_switch = False
        return {"killed": False}

    def _entry_order_ids(self) -> set[str]:
        if self.manager is None:
            return set()
        broker = getattr(self.manager.router, "broker", None)
        if broker is None:
            return set()
        out: set[str] = set()
        for order in getattr(broker, "orders", {}).values():
            purpose = getattr(getattr(order, "intent", None), "purpose", "")
            if purpose == "ENTRY":
                out.add(str(order.client_order_id))
        return out

    def _ack(
        self,
        row: dict[str, Any],
        status: str,
        reason: str | None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        cid = str(row.get("command_id") or row.get("id") or "")
        applied = _iso(self.clock.now()) if status == "applied" else None
        stored = self.store.update_ack(cid, status, reason, applied) if cid else dict(row)
        stored.update(row)
        stored["status"] = status
        stored["status_reason"] = reason
        stored["applied_ts"] = applied
        if extra:
            stored.update(extra)
        if self.ledger is not None and cid and hasattr(self.ledger, "ack_founder_command"):
            self.ledger.ack_founder_command(cid, status, reason, applied)
        self.last_ack = stored
        self._publish_ack(stored)
        return stored

    def _publish_ack(self, ack: dict[str, Any]) -> None:
        if self.bus is None:
            return
        self.bus.publish(
            "COMMAND_ACK",
            {
                "command_id": ack.get("command_id") or ack.get("id"),
                "status": ack.get("status"),
                "reason": ack.get("status_reason"),
                "kind": ack.get("kind"),
                "actor": ack.get("actor"),
                "available_ts": ack.get("available_ts"),
                "applied_ts": ack.get("applied_ts"),
                "who": ack.get("actor"),
                "when": ack.get("applied_ts") or ack.get("available_ts"),
                "why": ack.get("reason"),
            },
            source="control",
        )


def submit(
    handler: ControlHandler,
    kind: str,
    args: dict[str, Any],
    *,
    actor: str,
    reason: str,
    command_id: str,
    available_ts: datetime | str | None = None,
) -> dict[str, Any]:
    """Helper used by the gateway and tests. Rejects unknown args before apply."""
    kind = canonical_kind(kind)
    if kind in CONFIRM_KINDS:
        pass
    err = validate_args(kind, args)
    if err:
        return handler.apply(
            make_row(
                kind,
                args,
                actor=actor,
                reason=reason,
                available_ts=available_ts or handler.clock.now(),
                command_id=command_id,
                reject_reason=err,
            )
        )
    return handler.apply(
        make_row(
            kind,
            args,
            actor=actor,
            reason=reason,
            available_ts=available_ts or handler.clock.now(),
            command_id=command_id,
        )
    )
