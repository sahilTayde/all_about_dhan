"""Paper-only broker helpers for the desk. The live gate (DhanBroker) is not touched here."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime
from typing import Any, Callable

from brokers import InvalidTransition, Order, PaperBroker
from risk_engine import IST, RiskDecision


class ClockedPaperBroker(PaperBroker):
    """PaperBroker whose approval-age check runs on the session clock (tape time in replay).

    Every other approval check (approved, action, client_order_id) is PaperBroker's own.
    """

    def __init__(self, clock: Callable[[], datetime], **kw: Any) -> None:
        super().__init__(**kw)
        self.clock = clock

    def approval_problems(self, decision: Any, action: str, client_order_id: str) -> list[str]:
        if isinstance(decision, RiskDecision):
            decision = replace(decision, ts=decision.ts + (datetime.now(IST) - self.clock()))
        return super().approval_problems(decision, action, client_order_id)

    def fill_at(self, order: Order, price: float, ts: Any = None) -> Order:
        """Fill one working order at the paper engine's simulated price (other orders untouched).

        ponytail: the paper engine's working-limit fill model stays the source of truth for
        when and at what price a ticket fills; this broker books it (tick-rounded) and the
        ledger records it. A native PaperBroker fill model replaces this once parity is retired.
        """
        if not order.is_open:
            raise InvalidTransition(f"{order.client_order_id}: cannot fill a {order.state.value} order")
        self.ltp[order.intent.symbol] = float(price)
        self._fill(order, self._tick(float(price)), ts)
        return order


def client_order_id(trade_id: str, leg: str) -> str:
    """Deterministic id per ticket leg: same ticket retried = same id (broker idempotency)."""
    return "aad" + hashlib.sha1(f"{trade_id}|{leg}".encode()).hexdigest()[:24]


def option_symbol(underlying: str, strike: Any, side: str) -> str:
    try:
        k = f"{float(strike):g}"
    except (TypeError, ValueError):
        k = "NA"
    return f"{str(underlying).upper()} {k} {side}"


def ledger_exit_reason(reason: str) -> str:
    """Paper engine exit reason -> ledger.EXIT_REASONS (the engine's own reason stays on the trade row)."""
    r = str(reason)
    if r in ("STOP", "CANCEL_ADVERSE"):
        return "STOP_HIT"
    if r == "TARGET":
        return "TARGET_HIT"
    if r.startswith("FLATTEN"):
        return "FLATTEN_EOD"
    if r == "FOUNDER_KILL":
        return "KILL_SWITCH"
    if r.startswith("FOUNDER_"):
        return "FOUNDER_COMMAND"
    if r in ("CANCEL_HUMAN", "HUMAN_EXIT"):
        return "MANUAL"
    if r.startswith("CANCEL"):
        return "BOSS_OVERRIDE"
    return "TIME_EXIT"


def ledger_cancel_reason(reason: str) -> str:
    r = str(reason)
    if r == "FOUNDER_KILL":
        return "KILL_SWITCH"
    if r.startswith("FOUNDER_"):
        return "FOUNDER_COMMAND"
    if r == "CANCEL_HUMAN":
        return "USER_CANCEL"
    if r == "CANCEL_UNFILLED_FLAT":
        return "EOD"
    if r.startswith("CANCEL_UNFILLED") or r == "UNFILLED":
        return "TIMEOUT_UNFILLED"
    return "BOSS_CHANGED_MIND"
