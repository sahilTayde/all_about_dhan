"""Submit far-off LIMIT, cancel immediately. Inject a mock broker in CI."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from harness.broker import OrderPathBroker, make_broker
from harness.gates import require_gates
from harness.order import (
    HarnessOrderError,
    OffMarketIntent,
    default_intent,
    new_client_order_id,
    validate_off_market,
)


@dataclass(frozen=True)
class HarnessResult:
    ok: bool
    submitted: int
    cancelled: int
    fills: int
    transport: str
    states: tuple[str, ...] = field(default_factory=tuple)
    client_order_ids: tuple[str, ...] = field(default_factory=tuple)


def run_shadow_test(
    *,
    mode: str,
    env: Mapping[str, str],
    transport: str = "none",
    broker: OrderPathBroker | None = None,
    intent: OffMarketIntent | None = None,
    count: int = 1,
) -> HarnessResult:
    """Gates first. An injected broker is the CI path: no live client is built."""
    require_gates(mode=mode, env=env)
    if count < 1 or count > 5:
        raise HarnessOrderError("count must be 1..5")
    used: OrderPathBroker
    label: str
    if broker is not None:
        if getattr(broker, "is_live", False) is True:
            raise HarnessOrderError("injected broker must not be live in this harness")
        used = broker
        label = getattr(broker, "name", "mock") or "mock"
    else:
        used = make_broker(transport=transport, env=dict(env))
        label = transport
    submitted = 0
    cancelled = 0
    fills = 0
    states: list[str] = []
    ids: list[str] = []
    template = validate_off_market(intent or default_intent())
    for _ in range(count):
        one = OffMarketIntent(
            symbol=template.symbol,
            security_id=template.security_id,
            side=template.side,
            order_type=template.order_type,
            limit_price=template.limit_price,
            lots=template.lots,
            lot_size=template.lot_size,
            exchange=template.exchange,
            product_type=template.product_type,
            client_order_id=new_client_order_id(),
        )
        ack = used.place_limit(one)
        submitted += 1
        fills += int(ack.filled_qty)
        if ack.filled_qty:
            raise HarnessOrderError("off-market LIMIT filled; not a success")
        cancel = used.cancel(ack.broker_order_id)
        cancelled += 1
        fills += int(cancel.filled_qty)
        states.append(f"{ack.state}->{cancel.state}")
        ids.append(ack.client_order_id)
        if cancel.filled_qty:
            raise HarnessOrderError("cancel reported a fill")
        if cancel.state != "CANCELLED":
            raise HarnessOrderError(f"expected CANCELLED, got {cancel.state}")
    return HarnessResult(
        ok=True,
        submitted=submitted,
        cancelled=cancelled,
        fills=fills,
        transport=label,
        states=tuple(states),
        client_order_ids=tuple(ids),
    )
