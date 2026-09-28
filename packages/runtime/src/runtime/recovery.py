"""V2-10 restart sequence (architecture §3.5). Paper only."""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from brokers.fills import ClockedPaperBroker  # type: ignore[import-untyped]
from brokers.orders import Order, OrderState, Position  # type: ignore[import-untyped]
from brokers.reconcile import reconcile  # type: ignore[import-untyped]
from contracts.clock import IST, SimClock
from events.bus import MemoryBus
from ledger.migrate import check_schema
from ledger.v2 import SqliteLedgerStore, lots_from_qty
from risk_engine import RiskDecision, TradeIntent  # type: ignore[import-untyped]

from runtime.kernel import Engine, Handler
from runtime.services import write_engine_status
from runtime.sources import EnvelopeSource

log = logging.getLogger("runtime.recovery")

STALE_NEW_S = 30.0
FAULT_MATRIX_KILL_POINTS = (
    "after_new_before_submit",
    "after_broker_fill_before_ledger",
    "after_fill_before_stop",
)


@dataclass
class RecoveryResult:
    status: str
    recovered_orders: int
    recon_ok: bool
    mismatches: list[dict[str, Any]] = field(default_factory=list)
    rehydrate_mismatches: int = 0
    elapsed_s: float = 0.0
    halt_unreadable: bool = False
    stops_placed: int = 0


def rebuild_paper_broker(broker: ClockedPaperBroker | Any, store: SqliteLedgerStore) -> int:
    """Rebuild paper orders and positions from the durable ledger (same path as live)."""
    broker.orders.clear()
    if hasattr(broker, "_positions"):
        broker._positions.clear()
    n = 0
    for row in store.open_orders():
        qty = max(1, int(row.get("qty") or 1))
        symbol = str(row.get("symbol") or row.get("instrument_id") or "")
        lots, lot_size = lots_from_qty(qty, symbol)
        intent = TradeIntent(
            symbol=symbol,
            side=str(row.get("side") or "BUY"),
            lots=lots,
            lot_size=lot_size,
            order_type=str(row.get("order_type") or "LIMIT"),
            price=row.get("price"),
            trigger_price=row.get("trigger_price"),
            decision_price=row.get("decision_price"),
            purpose=str(row.get("purpose") or "ENTRY"),
            exit_reason=row.get("exit_reason"),
            instrument_id=str(row.get("instrument_id") or ""),
            client_order_id=str(row["client_order_id"]),
            stop_loss=row.get("trigger_price") if row.get("order_type") in ("SL", "SL-M") else None,
        )
        order = Order(intent=intent, broker="paper", mode="paper")
        try:
            order.state = OrderState(str(row["status"]))
        except ValueError:
            order.state = OrderState.NEW
        order.filled_qty = int(row.get("filled_qty") or 0)
        order.avg_fill_price = row.get("avg_fill_price")
        order.broker_order_id = row.get("broker_order_id")
        order.price = row.get("price")
        order.trigger_price = row.get("trigger_price")
        broker.orders[intent.client_order_id] = order
        if hasattr(broker, "remember"):
            broker.remember(intent.client_order_id)
        n += 1
    for pos in store.open_positions():
        p = Position(
            symbol=str(pos.get("symbol") or pos.get("instrument_id") or ""),
            net_qty=int(pos["net_qty"]),
            avg_price=float(pos.get("avg_price") or 0),
            instrument_id=str(pos.get("instrument_id") or ""),
        )
        if hasattr(broker, "_positions"):
            broker._positions[p.key] = p
        n += 1
    return n


def _handle_new_orders(store: SqliteLedgerStore, broker: Any, now: datetime) -> None:
    for row in store.open_orders():
        if str(row.get("status")) != "NEW":
            continue
        created = datetime.fromisoformat(str(row["created_at"]))
        if created.tzinfo is None:
            created = created.replace(tzinfo=IST)
        cid = str(row["client_order_id"])
        if (now - created).total_seconds() > STALE_NEW_S:
            store.mark_order_status(cid, "CANCELLED", cancel_reason="STALE_ON_RESTART")
            continue
        held = getattr(broker, "orders", {}).get(cid)
        if held is not None:
            store.mark_order_status(cid, held.state.value)


def _rebook_forced_closes(store: SqliteLedgerStore) -> bool:
    halts, unreadable = store.load_halts()
    if unreadable:
        return True
    for halt in halts:
        for close in halt.get("forced_closes") or []:
            if not isinstance(close, dict):
                return True
            store.book_forced_close(close)
    return False


def _recheck_stops(store: SqliteLedgerStore, broker: Any, clock: Any, risk: Any | None) -> int:
    placed = 0
    for pos in store.open_positions():
        key = str(pos.get("instrument_id") or pos.get("symbol") or "")
        if store.has_protective(key):
            continue
        stop_id = ("stop" + key.replace(":", "").replace("_", ""))[:27]
        if stop_id in getattr(broker, "orders", {}):
            store.set_protective(key, stop_id)
            continue
        trigger = 0.05
        plan = pos.get("exit_plan_json")
        if plan:
            with contextlib.suppress(json.JSONDecodeError, TypeError, ValueError):
                trigger = float(json.loads(plan).get("catastrophic_price") or trigger)
        qty = max(1, abs(int(pos.get("net_qty") or 1)))
        symbol = str(pos.get("symbol") or key)
        lots, lot_size = lots_from_qty(qty, symbol)
        intent = TradeIntent(
            symbol=symbol,
            side="SELL",
            lots=lots,
            lot_size=lot_size,
            order_type="SL-M",
            trigger_price=trigger,
            purpose="EXIT",
            exit_reason="STOP_HIT",
            instrument_id=key,
            client_order_id=stop_id,
        )
        ts = clock.now() if clock is not None else datetime.now(IST)
        rd = (
            risk.check_exit(intent, "EXIT", now=ts)
            if risk is not None
            else RiskDecision(True, stop_id, "EXIT", "OK", "recovery stop", ts)
        )
        if hasattr(broker, "place_order"):
            broker.place_order(intent, rd)
        store.insert_order(
            {
                "client_order_id": stop_id,
                "symbol": intent.symbol,
                "instrument_id": key,
                "side": "SELL",
                "qty": qty,
                "order_type": "SL-M",
                "trigger_price": trigger,
                "purpose": "EXIT",
                "state": "SUBMITTED",
                "account_id": pos.get("account_id") or "founder",
            }
        )
        store.set_protective(key, stop_id)
        placed += 1
    return placed


def recover(
    store: SqliteLedgerStore,
    *,
    broker: Any,
    clock: Any,
    state_dir: Path,
    source: EnvelopeSource | None = None,
    handlers: list[Handler] | None = None,
    bus: MemoryBus | None = None,
    risk: Any | None = None,
    role: str = "engine",
) -> RecoveryResult:
    """Store check → book load → reconcile → rehydrate → resume → stop re-check."""
    del role
    t0 = datetime.now(IST)
    check_schema(store.conn)
    now = clock.now()
    session = now.astimezone(IST).date().isoformat()
    store.load_book(session)
    recovered = rebuild_paper_broker(broker, store)
    _handle_new_orders(store, broker, now)
    raw = reconcile(broker, store, now)
    mismatches = [asdict(m) for m in raw]
    recon_ok = len(mismatches) == 0
    store.feed_status = "UP"
    halt_bad = _rebook_forced_closes(store)
    rehydrate_mismatches = 0
    if source is not None:
        last = store.get_last_checkpoint()
        last_id = last[0] if last else None
        pending: list[Any] = []
        skipping = last_id is not None
        for env in source:
            if skipping:
                if getattr(env, "event_id", None) == last_id:
                    skipping = False
                continue
            pending.append(env)
        if pending:
            first = datetime.fromisoformat(str(pending[0].available_ts))
            if first.tzinfo is None:
                first = first.replace(tzinfo=IST)
            engine = Engine(
                EnvelopeSource(pending),
                SimClock(first),
                bus or MemoryBus(),
                handlers or [],
                store,
                mode="rehydrate",
            )
            rehydrate_mismatches = engine.run().mismatches
            if rehydrate_mismatches:
                recon_ok = False
                log.critical("REHYDRATE_MISMATCH: %s", rehydrate_mismatches)
    stops = _recheck_stops(store, broker, clock, risk)
    elapsed = (datetime.now(IST) - t0).total_seconds()
    write_engine_status(state_dir, clock, restart=True)
    status_path = state_dir / "engine_status.json"
    body = json.loads(status_path.read_text(encoding="utf-8")) if status_path.is_file() else {}
    body.update(
        {
            "status": "READY",
            "restart": True,
            "recovered_orders": recovered,
            "recon_ok": recon_ok and not halt_bad,
            "ts": now.isoformat(timespec="seconds"),
        }
    )
    state_dir.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(body) + "\n", encoding="utf-8")
    log.info("recovery READY recovered_orders=%s recon_ok=%s elapsed=%.3fs", recovered, recon_ok, elapsed)
    return RecoveryResult(
        status="READY",
        recovered_orders=recovered,
        recon_ok=recon_ok and not halt_bad,
        mismatches=mismatches,
        rehydrate_mismatches=rehydrate_mismatches,
        elapsed_s=elapsed,
        halt_unreadable=halt_bad,
        stops_placed=stops,
    )
