"""V2 order router: risk before broker, deterministic ids, paper only."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, cast

from brokers.factory import LiveBrokerDisabled, make_broker
from brokers.fills import ClockedPaperBroker
from brokers.orders import Order, OrderState
from contracts.ids import order_id
from contracts.instruments import India
from contracts.payloads import Decision, EntryPlan, ExitPlan
from events.bus import MemoryBus
from ledger.charges import load_rates  # type: ignore[import-untyped, unused-ignore]
from risk_engine import RiskDecision, TradeIntent
from risk_engine.last_good import LastGood, V2RiskEngine

from oms.ledger_stub import MemoryLedger

_LIVEISH_NAMES = frozenset({"dhan", "live", "limited_live", "shadow"})


class PaperDeskBroker(Protocol):
    """Marker protocol: only paper brokers set `is_paper is True` and `mode == "paper"`."""

    is_paper: bool
    mode: str
    name: str
    orders: dict[str, Order]
    on_fill: Callable[..., None] | None

    def place_order(self, intent: TradeIntent, decision: RiskDecision) -> Order: ...

    def remember(self, client_order_id: str, **fields: Any) -> None: ...


def is_paper_desk_broker(broker: object) -> bool:
    """True only for a paper desk broker. Live-like name or mode is never paper."""
    return (
        getattr(broker, "is_paper", False) is True
        and getattr(broker, "mode", None) == "paper"
        and str(getattr(broker, "name", "") or "").lower() not in _LIVEISH_NAMES
    )


def require_paper_broker(broker: object) -> PaperDeskBroker:
    """Router boundary: refuse anything that is not a paper desk broker."""
    if isinstance(broker, ClockedPaperBroker) and is_paper_desk_broker(broker):
        return broker
    if is_paper_desk_broker(broker) and callable(getattr(broker, "place_order", None)):
        return cast(PaperDeskBroker, broker)
    raise LiveBrokerDisabled(
        "V2 paper-only: OrderRouter accepts only ClockedPaperBroker "
        "(or is_paper=True and mode='paper'); live/Dhan inject is refused"
    )


@dataclass(frozen=True)
class Account:
    account_id: str


@dataclass(frozen=True)
class Veto:
    client_order_id: str
    reason_code: str
    reason: str


def symbol_from_instrument(instrument_id: str) -> str:
    parts = India().parse_instrument_id(instrument_id)
    if parts["strike"] and parts["option_type"]:
        strike = parts["strike"].split(".")[0]
        return f"{parts['symbol']} {strike} {parts['option_type']}"
    return parts["symbol"]


def underlying_from_instrument(instrument_id: str) -> str:
    return India().parse_instrument_id(instrument_id)["symbol"]


def lot_size_for(instrument_id: str) -> int:
    return India().lot_size(underlying_from_instrument(instrument_id))


class OrderRouter:
    """Idempotent submit: risk first, then NEW row, then paper place."""

    def __init__(
        self,
        *,
        clock: Any,
        risk: V2RiskEngine | Any,
        broker: PaperDeskBroker | None = None,
        store: MemoryLedger | None = None,
        bus: MemoryBus | None = None,
        rates: LastGood | None = None,
    ) -> None:
        self.clock = clock
        self.risk = risk
        raw: object = broker if broker is not None else make_broker(mode="paper", clock=clock)
        self.broker = require_paper_broker(raw)
        self.store = store if store is not None else MemoryLedger()
        self.bus = bus if bus is not None else MemoryBus()
        self.rates = rates
        self._sync_rates()
        self.broker.on_fill = self._on_broker_fill

    def _sync_rates(self) -> None:
        if self.rates is None:
            return
        got = self.rates.get()
        self.store.rates = got

    def _intent(
        self,
        *,
        client_order_id: str,
        instrument_id: str,
        lots: int,
        lot_size: int,
        order_type: str,
        price: float | None,
        trigger: float | None,
        stop_loss: float | None,
        purpose: str,
        side: str,
        exit_reason: str | None = None,
    ) -> TradeIntent:
        return TradeIntent(
            symbol=symbol_from_instrument(instrument_id),
            side=side,
            lots=lots,
            lot_size=lot_size,
            order_type=order_type,
            price=price,
            trigger_price=trigger,
            decision_price=price,
            stop_loss=stop_loss,
            purpose=purpose,
            exit_reason=exit_reason,
            instrument_id=instrument_id,
            client_order_id=client_order_id,
        )

    def submit(self, plan: EntryPlan, decision: Decision, account: Account) -> Order | Veto:
        self._sync_rates()
        oid = order_id(account.account_id, plan.signal_id, "entry")
        existing = self.store.get_order(oid)
        if existing is not None and not existing.get("needs_lookup"):
            held = self.broker.orders.get(oid)
            if held is not None:
                return held
            return Veto(oid, "DUPLICATE", "order already recorded")
        if existing is not None and existing.get("needs_lookup"):
            held = self.broker.orders.get(oid)
            if held is not None:
                existing["needs_lookup"] = False
                return held
            existing["needs_lookup"] = False
            return self._place_adopt(existing, plan, decision, account, oid)
        if self.rates is not None and (self.rates.entries_blocked or self.rates.exits_only):
            return self._veto(oid, "CONFIG_INVALID", "cost config invalid; entries blocked")
        instrument_id = decision.instrument_id or ""
        lots = int(decision.lots or 0)
        lot_size = int(decision.lot_size or lot_size_for(instrument_id))
        stop = _catastrophic_price(plan, decision)
        intent = self._intent(
            client_order_id=oid,
            instrument_id=instrument_id,
            lots=lots,
            lot_size=lot_size,
            order_type="LIMIT",
            price=plan.limit_price,
            trigger=None,
            stop_loss=stop,
            purpose="ENTRY",
            side="BUY",
        )
        rd = self.risk.check_entry(intent, now=self.clock.now())
        self.store.record_decision(
            {
                "client_order_id": rd.client_order_id,
                "action": rd.action,
                "approved": rd.approved,
                "reason_code": rd.reason_code,
                "reason": rd.reason,
                "ts": rd.ts,
                "fingerprint": intent.fingerprint,
            }
        )
        if not rd.approved:
            return self._veto(oid, rd.reason_code, rd.reason)
        if existing is None:
            self.store.insert_order(
                {
                    "client_order_id": oid,
                    "state": OrderState.NEW.value,
                    "account_id": account.account_id,
                    "signal_id": plan.signal_id,
                    "instrument_id": instrument_id,
                    "lots": lots,
                    "lot_size": lot_size,
                    "purpose": "ENTRY",
                    "needs_lookup": False,
                    "stop_loss": stop,
                }
            )
        try:
            order = self.broker.place_order(intent, rd)
        except TimeoutError:
            self.store.mark_needs_lookup(oid)
            row = self.store.get_order(oid)
            if row is not None:
                row["needs_lookup"] = True
            raise
        self.broker.remember(
            oid,
            available_ts=self.clock.now(),
            decision_ts=self.clock.now(),
            moneyness=_moneyness(decision),
        )
        self.bus.publish(
            "ORDER_SUBMITTED",
            {"client_order_id": oid, "account_id": account.account_id},
            source="oms",
        )
        return order

    def _place_adopt(
        self,
        existing: dict[str, Any],
        plan: EntryPlan,
        decision: Decision,
        account: Account,
        oid: str,
    ) -> Order:
        """Lookup-by-id before resend. Risk already approved this client_order_id."""
        instrument_id = str(existing.get("instrument_id") or decision.instrument_id or "")
        lots = int(existing.get("lots") or decision.lots or 0)
        lot_size = int(existing.get("lot_size") or decision.lot_size or lot_size_for(instrument_id))
        intent = self._intent(
            client_order_id=oid,
            instrument_id=instrument_id,
            lots=lots,
            lot_size=lot_size,
            order_type="LIMIT",
            price=plan.limit_price,
            trigger=None,
            stop_loss=(
                float(existing["stop_loss"])
                if existing.get("stop_loss") is not None
                else _catastrophic_price(plan, decision)
            ),
            purpose="ENTRY",
            side="BUY",
        )
        rd = RiskDecision(True, oid, "ENTRY", "OK", "adopt", self.clock.now())
        try:
            order = self.broker.place_order(intent, rd)
        except TimeoutError:
            existing["needs_lookup"] = True
            raise
        self.broker.remember(
            oid,
            available_ts=self.clock.now(),
            decision_ts=self.clock.now(),
            moneyness=_moneyness(decision),
        )
        return order

    def _veto(self, oid: str, code: str, reason: str) -> Veto:
        self.bus.publish(
            "ENTRY_VETOED",
            {"client_order_id": oid, "reason_code": code, "reason": reason},
            source="oms",
        )
        return Veto(oid, code, reason)

    def _on_broker_fill(self, order: Order, qty: int, price: float, ts: Any) -> None:
        model = getattr(self.broker, "fill_models", {}).get(order.client_order_id, "fcmeas")
        self.store.record_fill(
            order.client_order_id,
            qty,
            price,
            fill_model=model,
            ts=self.clock.now(),
            side=order.intent.side,
            symbol=order.intent.symbol,
            instrument_id=order.intent.instrument_id,
        )
        self.bus.publish(
            "ORDER_FILLED",
            {
                "client_order_id": order.client_order_id,
                "qty": qty,
                "price": price,
                "fill_model": model,
            },
            source="oms",
        )
        if order.intent.purpose == "ENTRY":
            self._place_protective_stop(order)

    def _place_protective_stop(self, parent: Order) -> None:
        row = self.store.get_order(parent.client_order_id)
        account_id = (row or {}).get("account_id") or "founder"
        signal_id = (row or {}).get("signal_id") or parent.client_order_id
        stop_oid = order_id(str(account_id), str(signal_id), "stop")
        if stop_oid in self.broker.orders:
            self.store.set_protective(parent.intent.instrument_id or parent.intent.symbol, stop_oid)
            return
        trigger = parent.intent.stop_loss
        if trigger is None:
            trigger = 0.05
        intent = self._intent(
            client_order_id=stop_oid,
            instrument_id=parent.intent.instrument_id,
            lots=parent.intent.lots,
            lot_size=parent.intent.lot_size,
            order_type="SL-M",
            price=None,
            trigger=trigger,
            stop_loss=None,
            purpose="EXIT",
            side="SELL",
            exit_reason="STOP_HIT",
        )
        rd = self.risk.check_exit(intent, "EXIT", now=self.clock.now())
        self.broker.place_order(intent, rd)
        key = parent.intent.instrument_id or parent.intent.symbol
        self.store.set_protective(key, stop_oid)

    def exit(self, position: dict[str, Any], reason: str) -> Order:
        inst = str(position.get("instrument_id") or "")
        qty = int(position.get("net_qty") or 0)
        lot_size = lot_size_for(inst) if inst else 1
        lots = max(1, qty // lot_size) if lot_size else qty
        acc = str(position.get("account_id") or "founder")
        parent = str(position.get("entry_order_id") or "x")
        oid = order_id(acc, parent, "exit")
        intent = self._intent(
            client_order_id=oid,
            instrument_id=inst,
            lots=lots,
            lot_size=lot_size,
            order_type="MARKET",
            price=float(position.get("avg_price") or 0) or None,
            trigger=None,
            stop_loss=None,
            purpose="EXIT",
            side="SELL",
            exit_reason=reason,
        )
        rd = self.risk.check_exit(intent, "EXIT", now=self.clock.now())
        return self.broker.place_order(intent, rd)


def _catastrophic_price(plan: EntryPlan, decision: Decision) -> float | None:
    stretch = plan.stretch or {}
    raw = stretch.get("catastrophic_price")
    if raw is not None:
        return float(raw)
    loc = decision.entry_location or {}
    if "catastrophic_price" in loc:
        return float(loc["catastrophic_price"])
    if decision.limit_price:
        return max(0.05, float(decision.limit_price) - 1.0)
    return max(0.05, plan.limit_price - 1.0)


def _moneyness(decision: Decision) -> str:
    choice = (decision.shadow or {}).get("chosen") if decision.shadow else None
    if choice in ("ATM", "ITM100", "ITM200"):
        return str(choice)
    return "ITM100"


def load_cost_rates(path: Any, bus: Any | None = None) -> LastGood:
    def _load(p: Any) -> dict[str, Any]:
        rates: dict[str, Any] = load_rates(p, by_exchange=True)
        return rates

    lg = LastGood(path, _load, component="costs", bus=bus)
    lg.get()
    return lg


# Re-export types used by tests / later tickets.
__all__ = [
    "Account",
    "ExitPlan",
    "OrderRouter",
    "PaperDeskBroker",
    "Veto",
    "is_paper_desk_broker",
    "load_cost_rates",
    "lot_size_for",
    "require_paper_broker",
    "symbol_from_instrument",
]
