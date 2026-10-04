"""Order-path broker protocol: place LIMIT + cancel. Default never builds a live client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from harness.gates import HarnessRefused
from harness.order import HarnessOrderError, OffMarketIntent, validate_off_market

_LIVE_CTOR_CALLS = 0


@dataclass(frozen=True)
class OrderAck:
    client_order_id: str
    broker_order_id: str
    state: str
    filled_qty: int = 0


@dataclass(frozen=True)
class CancelAck:
    broker_order_id: str
    state: str
    filled_qty: int = 0


class OrderPathBroker(Protocol):
    """PR-002 order-path subset: submit a LIMIT, then cancel. Not a live desk broker."""

    name: str
    is_live: bool

    def place_limit(self, intent: OffMarketIntent) -> OrderAck: ...

    def cancel(self, broker_order_id: str) -> CancelAck: ...


@dataclass
class MockOrderBroker:
    """In-memory / recorded fixture broker. No network. Never a live Dhan client."""

    name: str = "mock"
    is_live: bool = False
    next_broker_id: int = 5001
    placed: list[OffMarketIntent] = field(default_factory=list)
    cancelled: list[str] = field(default_factory=list)
    fills: dict[str, int] = field(default_factory=dict)

    def place_limit(self, intent: OffMarketIntent) -> OrderAck:
        clean = validate_off_market(intent)
        self.placed.append(clean)
        oid = str(self.next_broker_id)
        self.next_broker_id += 1
        filled = int(self.fills.get(clean.client_order_id, 0))
        state = "FILLED" if filled else "ACKNOWLEDGED"
        return OrderAck(clean.client_order_id, oid, state, filled_qty=filled)

    def cancel(self, broker_order_id: str) -> CancelAck:
        if not broker_order_id:
            raise HarnessOrderError("cancel needs a broker_order_id")
        self.cancelled.append(broker_order_id)
        return CancelAck(broker_order_id, "CANCELLED", filled_qty=0)


def live_ctor_calls() -> int:
    """Test helper: how many times the live Dhan transport constructor ran."""
    return _LIVE_CTOR_CALLS


def note_live_ctor() -> None:
    global _LIVE_CTOR_CALLS
    _LIVE_CTOR_CALLS += 1


def make_broker(
    *,
    transport: str = "none",
    env: dict[str, str] | None = None,
) -> OrderPathBroker:
    """Default transport is off. ``dhan`` is imported only after an explicit request."""
    cleaned = (transport or "none").strip().lower()
    if cleaned in {"mock", "recorded"}:
        return MockOrderBroker(name=cleaned)
    if cleaned == "dhan":
        from harness.dhan_live import build_dhan_live_broker

        return build_dhan_live_broker(env or {})
    raise HarnessRefused(
        "TRANSPORT_OFF",
        "default path never constructs a live client; pass transport mock|recorded|dhan",
    )
