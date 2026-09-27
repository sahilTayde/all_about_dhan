"""Broker-agnostic core: order state machine, BrokerAdapter interface, positions."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from risk_engine import IST, RiskDecision, TradeIntent

log = logging.getLogger("brokers")


class OrderState(str, Enum):
    NEW = "NEW"
    SUBMITTED = "SUBMITTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


S = OrderState
TRANSITIONS: dict[OrderState, frozenset[OrderState]] = {
    S.NEW: frozenset({S.SUBMITTED, S.REJECTED, S.CANCELLED}),
    S.SUBMITTED: frozenset({S.PARTIAL, S.FILLED, S.REJECTED, S.CANCELLED, S.EXPIRED}),
    S.PARTIAL: frozenset({S.PARTIAL, S.FILLED, S.CANCELLED, S.EXPIRED}),
}
TERMINAL = frozenset({S.FILLED, S.REJECTED, S.CANCELLED, S.EXPIRED})


class InvalidTransition(Exception):
    pass


class LedgerWriteFailed(Exception):
    """The ``on_transition`` hook (ledger) raised; the order kept its previous state (no orphan)."""


class OrderRefused(Exception):
    """No valid, fresh, matching risk approval."""


class LiveOrderRefused(OrderRefused):
    """The live gate (mode + founder env confirmation + risk approval) is not fully open."""


@dataclass
class Position:
    symbol: str
    net_qty: int
    avg_price: float = 0.0
    instrument_id: str = ""

    @property
    def key(self) -> str:
        return self.instrument_id or self.symbol


@dataclass(frozen=True)
class OrderSnapshot:
    """The broker's view of one order (for reconciliation)."""

    client_order_id: str
    broker_order_id: str
    state: Optional[OrderState]
    filled_qty: int = 0
    symbol: str = ""


Hook = Callable[..., None]


@dataclass
class Order:
    intent: TradeIntent
    broker: str
    mode: str = "paper"
    state: OrderState = S.NEW
    broker_order_id: Optional[str] = None
    filled_qty: int = 0
    avg_fill_price: Optional[float] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    target: Optional[float] = None
    stop_loss: Optional[float] = None
    trailing_jump: Optional[float] = None
    is_super: bool = False
    cancel_reason: Optional[str] = None
    needs_lookup: bool = False  # submit got no response: ask the broker before resending
    history: list[dict[str, Any]] = field(default_factory=list)
    on_transition: Optional[Hook] = field(default=None, repr=False)
    on_fill: Optional[Hook] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        i = self.intent
        self.price = self.price if self.price is not None else i.price
        self.trigger_price = self.trigger_price if self.trigger_price is not None else i.trigger_price
        self.target = self.target if self.target is not None else i.target
        self.stop_loss = self.stop_loss if self.stop_loss is not None else i.stop_loss
        self.trailing_jump = self.trailing_jump if self.trailing_jump is not None else i.trailing_jump

    @property
    def client_order_id(self) -> str:
        return self.intent.client_order_id

    @property
    def remaining_qty(self) -> int:
        return self.intent.qty - self.filled_qty

    @property
    def is_open(self) -> bool:
        return self.state not in TERMINAL

    def transition(self, to: OrderState, reason: str = "") -> None:
        if to not in TRANSITIONS.get(self.state, ()):
            raise InvalidTransition(f"{self.client_order_id}: {self.state.value} -> {to.value} not allowed")
        prev, self.state = self.state, to
        entry = {"ts": datetime.now(IST).isoformat(timespec="milliseconds"), "from": prev.value, "to": to.value, "reason": reason}
        self.history.append(entry)
        if self.on_transition:
            try:
                self.on_transition(self, prev, to, reason)
            except Exception as exc:  # the ledger did not record it: the broker must not either
                self.state = prev
                if self.history and self.history[-1] is entry:
                    self.history.pop()
                raise LedgerWriteFailed(f"{self.client_order_id}: {prev.value} -> {to.value} not recorded: {exc}") from exc
        log.info("order %s %s -> %s %s", self.client_order_id, prev.value, to.value, reason)

    def apply_fill(self, qty: int, price: float, ts: Any = None) -> None:
        if self.state not in (S.SUBMITTED, S.PARTIAL):
            raise InvalidTransition(f"{self.client_order_id}: cannot fill in state {self.state.value}")
        if qty <= 0 or qty > self.remaining_qty:
            raise ValueError(f"{self.client_order_id}: fill qty {qty} outside 1..{self.remaining_qty}")
        value = (self.avg_fill_price or 0.0) * self.filled_qty + price * qty
        self.filled_qty += qty
        self.avg_fill_price = round(value / self.filled_qty, 4)
        if self.on_fill:
            self.on_fill(self, qty, price, ts)
        self.transition(S.FILLED if self.remaining_qty == 0 else S.PARTIAL, f"fill {qty} @ {price}")

    def as_row(self) -> dict[str, Any]:
        i = self.intent
        return {
            "client_order_id": i.client_order_id, "broker_order_id": self.broker_order_id, "trade_id": i.trade_id,
            "broker": self.broker, "mode": self.mode, "symbol": i.symbol, "instrument_id": i.instrument_id,
            "side": i.side, "qty": i.qty, "order_type": i.order_type, "price": self.price,
            "trigger_price": self.trigger_price, "decision_price": i.decision_price, "purpose": i.purpose,
            "filled_qty": self.filled_qty, "avg_fill_price": self.avg_fill_price, "exit_reason": i.exit_reason,
            "cancel_reason": self.cancel_reason,
        }


def exit_intent(
    position: Position, *, exit_reason: str, decision_price: Optional[float] = None,
    exchange: str = "NSE_FNO", product_type: str = "INTRADAY",
) -> TradeIntent:
    """MARKET order that takes `position` to flat (qty expressed as lots of 1)."""
    return TradeIntent(
        symbol=position.symbol, side="SELL" if position.net_qty > 0 else "BUY", lots=abs(position.net_qty),
        lot_size=1, purpose="EXIT", exit_reason=exit_reason, decision_price=decision_price,
        instrument_id=position.instrument_id, exchange=exchange, product_type=product_type,
    )


class BrokerAdapter(ABC):
    """India (Dhan, paper) now; a Forex broker later implements the same methods.

    Every call that sends or changes an order takes the RiskDecision that approved it.
    """

    name = "base"
    mode = "paper"
    max_decision_age_s = 30.0

    def __init__(self) -> None:
        self.orders: dict[str, Order] = {}
        self.on_transition: Optional[Hook] = None
        self.on_fill: Optional[Hook] = None

    def _register(self, intent: TradeIntent, **kw: Any) -> Order:
        order = Order(intent=intent, broker=self.name, mode=self.mode,
                      on_transition=self._emit_transition, on_fill=self._emit_fill, **kw)
        self.orders[intent.client_order_id] = order
        return order

    def _emit_transition(self, *args: Any) -> None:
        if self.on_transition:
            self.on_transition(*args)

    def _emit_fill(self, *args: Any) -> None:
        if self.on_fill:
            self.on_fill(*args)

    @staticmethod
    def action_for(intent: TradeIntent) -> str:
        return "ENTRY" if intent.purpose == "ENTRY" else "EXIT"

    def approval_problems(self, decision: Any, action: str, client_order_id: str) -> list[str]:
        if not isinstance(decision, RiskDecision):
            return ["no risk decision"]
        problems = []
        if not decision.approved:
            problems.append(f"risk vetoed ({decision.reason_code})")
        if decision.action != action:
            problems.append(f"decision is for {decision.action}, not {action}")
        if decision.client_order_id != client_order_id:
            problems.append("decision is for a different order")
        age = (datetime.now(IST) - decision.ts).total_seconds()
        if not -5 <= age <= self.max_decision_age_s:
            problems.append(f"decision is {age:.0f}s old (max {self.max_decision_age_s:.0f}s)")
        return problems

    def require_approval(self, decision: Any, action: str, client_order_id: str) -> None:
        problems = self.approval_problems(decision, action, client_order_id)
        if problems:
            log.error("ORDER REFUSED %s %s %s: %s", self.name, action, client_order_id, "; ".join(problems))
            raise OrderRefused("; ".join(problems))

    def exit_position(self, intent: TradeIntent, decision: RiskDecision) -> Order:
        if intent.purpose != "EXIT":
            raise ValueError("exit_position needs an EXIT intent (see exit_intent)")
        return self.place_order(intent, decision)

    @abstractmethod
    def place_order(self, intent: TradeIntent, decision: RiskDecision) -> Order: ...

    @abstractmethod
    def place_super_order(self, intent: TradeIntent, decision: RiskDecision) -> Order:
        """Entry + target + stop loss (+ trailing jump) as one order."""

    @abstractmethod
    def modify_order(
        self, order: Order, decision: RiskDecision, *, price: Optional[float] = None,
        trigger_price: Optional[float] = None, target: Optional[float] = None,
        stop_loss: Optional[float] = None, trailing_jump: Optional[float] = None,
    ) -> Order: ...

    @abstractmethod
    def cancel_order(self, order: Order, decision: RiskDecision, reason: str = "USER_CANCEL") -> Order: ...

    @abstractmethod
    def flatten_all(self, decision: RiskDecision) -> Any:
        """Kill switch: cancel every open order and exit every position."""

    @abstractmethod
    def get_order_status(self, order: Order) -> Order:
        """Refresh `order` from the broker (fills and state transitions applied)."""

    @abstractmethod
    def get_positions(self) -> list[Position]: ...

    @abstractmethod
    def get_orders(self) -> list[OrderSnapshot]: ...

    @abstractmethod
    def get_balance(self) -> float: ...


def attach_ledger(broker: BrokerAdapter, ledger: Any) -> None:
    """Persist every transition and fill of `broker`'s orders to a ledger.Ledger."""
    broker.on_transition = lambda order, prev, to, reason: ledger.record_order(
        order.as_row(), prev.value, to.value, reason
    )
    broker.on_fill = lambda order, qty, price, ts: ledger.record_fill(order.client_order_id, qty, price, ts)
