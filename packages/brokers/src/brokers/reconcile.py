"""Compare the broker's positions/orders with the internal book; alarm on any mismatch.

A mismatch is written to the ledger's recon_runs, which halts new entries in the risk engine
(RECON_MISMATCH) and raises a health alert, until a later run is clean.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Optional

from brokers.orders import BrokerAdapter, OrderSnapshot, OrderState, Position

log = logging.getLogger("brokers.reconcile")


@dataclass(frozen=True)
class Mismatch:
    kind: str  # QTY_MISMATCH | ORPHAN_BROKER | ORPHAN_INTERNAL | ORDER_STATE_MISMATCH |
    #            ORDER_MISSING_AT_BROKER | ORPHAN_BROKER_ORDER | RECON_ERROR
    key: str
    internal: Any = None
    broker: Any = None


def compare_positions(internal: list[Position], broker: list[Position]) -> list[Mismatch]:
    ours = {p.key: p.net_qty for p in internal if p.net_qty}
    theirs = {p.key: p.net_qty for p in broker if p.net_qty}
    out = []
    for key in sorted(set(ours) | set(theirs)):
        a, b = ours.get(key), theirs.get(key)
        if a is None:
            out.append(Mismatch("ORPHAN_BROKER", key, None, b))
        elif b is None:
            out.append(Mismatch("ORPHAN_INTERNAL", key, a, None))
        elif a != b:
            out.append(Mismatch("QTY_MISMATCH", key, a, b))
    return out


def compare_orders(internal_open: list[dict[str, Any]], broker: list[OrderSnapshot]) -> list[Mismatch]:
    """internal_open: ledger.open_orders() rows (client_order_id, status). NEW orders were never sent."""
    theirs = {s.client_order_id: s for s in broker if s.client_order_id}
    ours = {o["client_order_id"]: o["status"] for o in internal_open if o["status"] != OrderState.NEW.value}
    out = []
    for cid, status in sorted(ours.items()):
        snap = theirs.get(cid)
        if snap is None:
            out.append(Mismatch("ORDER_MISSING_AT_BROKER", cid, status, None))
        elif snap.state is None or snap.state.value != status:
            out.append(Mismatch("ORDER_STATE_MISMATCH", cid, status, snap.state.value if snap.state else None))
    for snap in broker:
        if snap.state in (OrderState.SUBMITTED, OrderState.PARTIAL) and snap.client_order_id not in ours:
            out.append(Mismatch("ORPHAN_BROKER_ORDER", snap.client_order_id or snap.broker_order_id, None, snap.state.value))
    return out


def reconcile(broker: BrokerAdapter, ledger: Any, now: Optional[Any] = None) -> list[Mismatch]:
    """Run once (the desk calls this every minute). Broker errors count as a mismatch: fail closed."""
    try:
        internal = [
            Position(r["symbol"], r["net_qty"], r["avg_price"], r["instrument_id"] or "")
            for r in ledger.open_positions()
        ]
        mismatches = compare_positions(internal, broker.get_positions())
        mismatches += compare_orders(ledger.open_orders(), broker.get_orders())
    except Exception as exc:
        mismatches = [Mismatch("RECON_ERROR", broker.name, None, f"{type(exc).__name__}: {exc}")]
    ledger.record_recon([asdict(m) for m in mismatches], now)
    if mismatches:
        log.error("RECONCILIATION MISMATCH ALARM (%s): %s", broker.name, [asdict(m) for m in mismatches])
    return mismatches
