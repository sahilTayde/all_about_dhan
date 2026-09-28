"""V2 order router: risk before broker, deterministic ids, paper only."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, Protocol, cast

from brokers.factory import LiveBrokerDisabled, make_broker
from brokers.fills import ClockedPaperBroker, ModifyUnsupported, Quote
from brokers.orders import Order, OrderRefused, OrderState, Position, exit_intent
from contracts.ids import order_id
from contracts.instruments import India
from contracts.payloads import Decision, EntryPlan, ExitPlan
from events.bus import MemoryBus
from ledger.charges import load_rates  # type: ignore[import-untyped, unused-ignore]
from risk_engine import RiskDecision, TradeIntent
from risk_engine.last_good import LastGood, V2RiskEngine

from oms.exits import whole_lots_qty
from oms.ledger_stub import MemoryLedger

_LIVEISH_NAMES = frozenset({"dhan", "live", "limited_live", "shadow"})
_STOP_RESIZE_ATTEMPTS = 3
_STOP_RESIZE_FAILED = "STOP_RESIZE_FAILED"
_LOG = logging.getLogger(__name__)
_LOT_SIZE_MISMATCH = "LOT_SIZE_MISMATCH"
_QTY_NOT_WHOLE_LOT = "QTY_NOT_WHOLE_LOT"
_ODD_LOT_FLATTEN = "ODD_LOT_FLATTEN"


class PaperDeskBroker(Protocol):
    """Marker protocol: only paper brokers set `is_paper is True` and `mode == "paper"`."""

    is_paper: bool
    mode: str
    name: str
    orders: dict[str, Order]
    on_fill: Callable[..., None] | None
    fill_models: dict[str, str]

    def place_order(self, intent: TradeIntent, decision: RiskDecision) -> Order: ...

    def remember(self, client_order_id: str, **fields: Any) -> None: ...

    def cancel_order(
        self, order: Order, decision: RiskDecision, reason: str = "USER_CANCEL"
    ) -> Order: ...

    def modify_order(self, order_id: str, qty: int) -> Order: ...

    def on_depth(self, quote: Quote) -> None: ...

    def _fill(self, order: Order, px: float, ts: Any) -> None: ...


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
        return cast(PaperDeskBroker, broker)
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
        self.positions: Any | None = None
        self._exit_seq = 0
        self._stop_seq = 0
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

    def submit(
        self,
        plan: EntryPlan,
        decision: Decision,
        account: Account,
        *,
        exit_plan: ExitPlan | None = None,
    ) -> Order | Veto:
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
        lot_size = lot_size_for(instrument_id)
        if decision.lot_size is not None and int(decision.lot_size) != lot_size:
            return self._lot_mismatch_veto(oid, int(decision.lot_size), lot_size, "decision")
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
                    "exit_plan": exit_plan,
                }
            )
        if exit_plan is not None and self.positions is not None:
            self.positions.remember_plan(oid, exit_plan)
        placed = self._place_entry(intent, rd, oid)
        if isinstance(placed, Veto):
            return placed
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
        return placed

    def _place_adopt(
        self,
        existing: dict[str, Any],
        plan: EntryPlan,
        decision: Decision,
        account: Account,
        oid: str,
    ) -> Order | Veto:
        """Lookup-by-id before resend. Risk already approved this client_order_id."""
        instrument_id = str(existing.get("instrument_id") or decision.instrument_id or "")
        lots = int(existing.get("lots") or decision.lots or 0)
        lot_size = lot_size_for(instrument_id)
        stored = existing.get("lot_size")
        if stored is not None and int(stored) != lot_size:
            _LOG.error(
                "rebuild refused: stored lot_size %s != exchange %s for %s",
                stored,
                lot_size,
                instrument_id,
            )
            return self._lot_mismatch_veto(oid, int(stored), lot_size, "stored")
        if decision.lot_size is not None and int(decision.lot_size) != lot_size:
            _LOG.error(
                "rebuild refused: decision lot_size %s != exchange %s for %s",
                decision.lot_size,
                lot_size,
                instrument_id,
            )
            return self._lot_mismatch_veto(oid, int(decision.lot_size), lot_size, "decision")
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
            placed = self._place_entry(intent, rd, oid)
        except TimeoutError:
            existing["needs_lookup"] = True
            raise
        if isinstance(placed, Veto):
            return placed
        self.broker.remember(
            oid,
            available_ts=self.clock.now(),
            decision_ts=self.clock.now(),
            moneyness=_moneyness(decision),
        )
        return placed

    def _lot_mismatch_veto(self, oid: str, claimed: int, exchange: int, source: str) -> Veto:
        _LOG.error(
            "LOT_SIZE_MISMATCH %s claimed=%s exchange=%s oid=%s",
            source,
            claimed,
            exchange,
            oid,
        )
        return self._veto(
            oid,
            _LOT_SIZE_MISMATCH,
            f"{source} lot_size {claimed} != exchange {exchange}",
        )

    def _place_entry(self, intent: TradeIntent, rd: RiskDecision, oid: str) -> Order | Veto:
        """Send-time guard: qty > 0 and a whole multiple of the exchange lot."""
        exchange = lot_size_for(intent.instrument_id)
        qty = int(intent.qty)
        if qty <= 0 or qty % exchange != 0:
            return self._veto(
                oid,
                _QTY_NOT_WHOLE_LOT,
                f"qty {qty} is not a positive whole multiple of lot {exchange}",
            )
        try:
            return self.broker.place_order(intent, rd)
        except TimeoutError:
            self.store.mark_needs_lookup(oid)
            row = self.store.get_order(oid)
            if row is not None:
                row["needs_lookup"] = True
            raise

    def _veto(self, oid: str, code: str, reason: str) -> Veto:
        self.bus.publish(
            "ENTRY_VETOED",
            {"client_order_id": oid, "reason_code": code, "reason": reason},
            source="oms",
        )
        return Veto(oid, code, reason)

    def _on_broker_fill(self, order: Order, qty: int, price: float, ts: Any) -> None:
        model = getattr(self.broker, "fill_models", {}).get(order.client_order_id, "fcmeas")
        row = self.store.get_order(order.client_order_id)
        account_id = str((row or {}).get("account_id") or "founder")
        self.store.record_fill(
            order.client_order_id,
            qty,
            price,
            fill_model=model,
            ts=self.clock.now(),
            side=order.intent.side,
            symbol=order.intent.symbol,
            instrument_id=order.intent.instrument_id,
            account_id=account_id,
        )
        if self.positions is not None:
            plan = (row or {}).get("exit_plan")
            self.positions.on_fill(
                client_order_id=order.client_order_id,
                qty=qty,
                price=price,
                side=order.intent.side,
                instrument_id=order.intent.instrument_id,
                symbol=order.intent.symbol,
                account_id=account_id,
                entry_order_id=str((row or {}).get("signal_id") or order.client_order_id),
                exit_plan=plan,
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
        elif order.intent.side == "SELL":
            self._sync_stop_after_sell(order, account_id)
        # apply_fill invokes this hook before the order leaves SUBMITTED; assert after.

    def _place_protective_stop(self, parent: Order) -> None:
        key = parent.intent.instrument_id or parent.intent.symbol
        live = self.store.positions.get(key) or {}
        remaining = int(live.get("net_qty") or (parent.intent.lots * parent.intent.lot_size))
        row = self.store.get_order(parent.client_order_id)
        ctx = {
            "instrument_id": parent.intent.instrument_id,
            "symbol": parent.intent.symbol,
            "account_id": (row or {}).get("account_id") or live.get("account_id") or "founder",
            "entry_order_id": (row or {}).get("signal_id")
            or live.get("entry_order_id")
            or parent.client_order_id,
            "stop_price": parent.intent.stop_loss or live.get("stop_price") or 0.05,
            "lot_size": parent.intent.lot_size,
        }
        self.sync_protective_stop(ctx, remaining)

    def _sync_stop_after_sell(self, order: Order, account_id: str) -> None:
        key = order.intent.instrument_id or order.intent.symbol
        live = self.store.positions.get(key)
        remaining = int(live["net_qty"]) if live else 0
        ctx = (
            dict(live)
            if live
            else {
                "instrument_id": order.intent.instrument_id,
                "symbol": order.intent.symbol,
                "account_id": account_id,
                "entry_order_id": order.intent.instrument_id,
                "stop_price": 0.05,
            }
        )
        self.sync_protective_stop(ctx, remaining, keep=order.client_order_id)
        if remaining <= 0:
            self._cancel_sibling_exits(key, keep=order.client_order_id)

    def _stop_signal_id(self, position: dict[str, Any]) -> str:
        entry_oid = str(position.get("entry_order_id") or "")
        row = self.store.get_order(entry_oid) if entry_oid else None
        if row and row.get("signal_id"):
            return str(row["signal_id"])
        if entry_oid and not entry_oid.startswith("aad"):
            return entry_oid
        return str(position.get("position_id") or entry_oid or "x")

    def _open_stop_orders(self, key: str) -> list[Order]:
        out: list[Order] = []
        for order in self.broker.orders.values():
            if not order.is_open:
                continue
            if order.intent.purpose != "EXIT":
                continue
            if (order.intent.exit_reason or "") != "STOP_HIT":
                continue
            inst = order.intent.instrument_id or order.intent.symbol
            if inst == key:
                out.append(order)
        return out

    def open_stop_qty(self, key: str) -> int:
        total = 0
        for order in self._open_stop_orders(key):
            lot = int(order.intent.lot_size or 1)
            total += int(order.intent.lots) * lot
        return total

    def _cancel_sibling_exits(self, key: str, *, keep: str) -> None:
        """After a flatten fill, drop any other working EXIT so we cannot go short."""
        for order in list(self.broker.orders.values()):
            if order.client_order_id == keep or not order.is_open:
                continue
            if order.intent.purpose != "EXIT":
                continue
            inst = order.intent.instrument_id or order.intent.symbol
            if inst != key:
                continue
            self._cancel_stop(order, reason="POSITION_FLAT")

    def _cancel_stop(self, order: Order, reason: str = "STOP_REPLACE") -> None:
        if not order.is_open:
            return
        intent = self._intent(
            client_order_id=order.client_order_id,
            instrument_id=order.intent.instrument_id,
            lots=int(order.intent.lots),
            lot_size=int(order.intent.lot_size or 1),
            order_type="SL-M",
            price=None,
            trigger=order.trigger_price or order.intent.trigger_price,
            stop_loss=None,
            purpose="EXIT",
            side="SELL",
            exit_reason="STOP_HIT",
        )
        rd = self.risk.check_exit(intent, "CANCEL", now=self.clock.now())
        self.broker.cancel_order(order, rd, reason=reason)

    def sync_protective_stop(
        self,
        position: dict[str, Any],
        remaining_qty: int,
        *,
        keep: str | None = None,
    ) -> None:
        """Keep open STOP_HIT qty == remaining whole-lot qty (0 when flat).

        Prefer in-place ``modify_order(order_id, qty)``. Cancel-then-replace only
        when modify is unsupported. A failed resize retries the same replacement
        id, then CRITICAL-alerts and flattens the live book so it is never open
        without a stop. Never restores a stop larger than live net.
        """
        inst = str(position.get("instrument_id") or "")
        key = inst or str(position.get("symbol") or "")
        if not key:
            return
        lot = lot_size_for(inst) if inst else int(position.get("lot_size") or 1)
        remaining = whole_lots_qty(max(0, int(remaining_qty)), lot)
        live = self.store.positions.get(key)
        live_net = int(live["net_qty"]) if live is not None else remaining
        remaining = min(remaining, whole_lots_qty(max(0, live_net), lot))
        open_stops = [o for o in self._open_stop_orders(key) if o.client_order_id != keep]
        if remaining <= 0:
            for order in open_stops:
                self._cancel_stop(order, reason="POSITION_FLAT")
            self.store.protective.pop(key, None)
            return
        if len(open_stops) == 1:
            cur = open_stops[0]
            cur_qty = int(cur.intent.lots) * int(cur.intent.lot_size or lot)
            if cur_qty == remaining:
                self.store.set_protective(key, cur.client_order_id)
                return
            result = self._resize_stop_in_place(cur, remaining)
            if result == "ok":
                self.store.set_protective(key, cur.client_order_id)
                return
            if result == "failed":
                self._failsafe_flatten_naked(live or position, key)
                return
        trigger: float | None = None
        for order in open_stops:
            raw_px = order.trigger_price or order.intent.trigger_price or 0
            trigger = trigger or float(raw_px) or None
            self._cancel_stop(order, reason="STOP_REPLACE")
        if trigger is None:
            trigger = float(position.get("stop_price") or 0) or 0.05
        new_oid = self._next_stop_oid(position)
        if self._place_stop_with_retry(key, new_oid, remaining, lot, float(trigger), inst):
            self.store.set_protective(key, new_oid)
            return
        self._failsafe_flatten_naked(live or position, key)

    def _next_stop_oid(self, position: dict[str, Any]) -> str:
        acc = str(position.get("account_id") or "founder")
        signal = self._stop_signal_id(position)
        first = order_id(acc, signal, "stop")
        if first not in self.broker.orders:
            return first
        self._stop_seq += 1
        new_oid = order_id(acc, signal, f"stop{self._stop_seq}")
        while new_oid in self.broker.orders:
            self._stop_seq += 1
            new_oid = order_id(acc, signal, f"stop{self._stop_seq}")
        return new_oid

    def _resize_stop_in_place(self, order: Order, qty: int) -> str:
        """Return 'ok', 'unsupported', or 'failed' after bounded modify retries."""
        fn = getattr(self.broker, "modify_order", None)
        if not callable(fn):
            return "unsupported"
        last_err: Exception | None = None
        for _ in range(_STOP_RESIZE_ATTEMPTS):
            try:
                fn(order.client_order_id, qty)
            except ModifyUnsupported:
                return "unsupported"
            except TypeError:
                return "unsupported"
            except Exception as exc:
                last_err = exc
                continue
            lot = int(order.intent.lot_size or 1)
            now_qty = int(order.intent.lots) * lot
            if order.is_open and now_qty == qty:
                return "ok"
            last_err = OrderRefused(f"modify left qty {now_qty}, want {qty}")
        _ = last_err
        return "failed"

    def _place_stop_with_retry(
        self,
        key: str,
        new_oid: str,
        remaining: int,
        lot: int,
        trigger: float,
        inst: str,
    ) -> bool:
        live = self.store.positions.get(key)
        live_net = int(live["net_qty"]) if live is not None else remaining
        place_qty = min(remaining, whole_lots_qty(max(0, live_net), lot))
        if place_qty <= 0 or place_qty > live_net:
            return False
        intent = self._intent(
            client_order_id=new_oid,
            instrument_id=inst or key,
            lots=place_qty // lot,
            lot_size=lot,
            order_type="SL-M",
            price=None,
            trigger=float(trigger),
            stop_loss=None,
            purpose="EXIT",
            side="SELL",
            exit_reason="STOP_HIT",
        )
        for _ in range(_STOP_RESIZE_ATTEMPTS):
            rd = self._approve_reduce_only(intent, "EXIT")
            try:
                order = self.broker.place_order(intent, rd)
            except Exception:
                continue
            if not order.is_open or order.client_order_id != new_oid:
                continue
            placed = int(order.intent.lots) * int(order.intent.lot_size or lot)
            if placed > place_qty:
                self._cancel_stop(order, reason="STOP_OVERSIZE")
                continue
            if placed == place_qty:
                return True
        return False

    def _approve_reduce_only(self, intent: TradeIntent, action: str) -> RiskDecision:
        rd = self.risk.check_exit(intent, action, now=self.clock.now())
        if rd.approved:
            return rd
        if rd.reason_code == "MODE_NOT_ENABLED":
            return rd
        live = self.store.positions.get(intent.instrument_id or intent.symbol)
        net = int(live["net_qty"]) if live is not None else 0
        if intent.side == "SELL" and intent.purpose == "EXIT" and 0 < intent.qty <= net:
            return RiskDecision(
                True,
                intent.client_order_id,
                action,
                "OK_REDUCE_ONLY",
                "reduce-only SELL <= net cannot be vetoed",
                self.clock.now(),
            )
        return rd

    def _failsafe_flatten_naked(self, position: dict[str, Any], key: str) -> None:
        """CRITICAL alert + paper market flatten so the book is never open without a stop."""
        live = self.store.positions.get(key)
        inst = str((live or position).get("instrument_id") or key)
        lot = lot_size_for(inst) if inst else int(position.get("lot_size") or 1)
        flatten_qty = whole_lots_qty(int((live or position).get("net_qty") or 0), lot)
        detail = f"protective stop resize failed; flattening {flatten_qty}"
        if self.positions is not None:
            self.positions._alert(_STOP_RESIZE_FAILED, key, detail, severity="CRITICAL")
        else:
            self.bus.publish(
                "HEALTH_ALERT",
                {
                    "reason_code": _STOP_RESIZE_FAILED,
                    "instrument_id": key,
                    "detail": detail,
                    "severity": "CRITICAL",
                    "ts": self.clock.now().isoformat(),
                },
                source="oms",
            )
        for order in list(self._open_stop_orders(key)):
            self._cancel_stop(order, reason=_STOP_RESIZE_FAILED)
        self.store.protective.pop(key, None)
        if flatten_qty <= 0:
            return
        acc = str((live or position).get("account_id") or "founder")
        parent = str(
            (live or position).get("entry_order_id") or (live or position).get("position_id") or "x"
        )
        self._exit_seq += 1
        oid = order_id(acc, parent, f"exit{self._exit_seq}")
        hint = (
            (live or position).get("last_good_quote")
            or (live or position).get("exit_price_hint")
            or (live or position).get("avg_price")
            or 0.05
        )
        intent = self._intent(
            client_order_id=oid,
            instrument_id=inst,
            lots=flatten_qty // lot,
            lot_size=lot,
            order_type="MARKET",
            price=None,
            trigger=None,
            stop_loss=None,
            purpose="EXIT",
            side="SELL",
            exit_reason=_STOP_RESIZE_FAILED,
        )
        rd = self._approve_reduce_only(intent, "EXIT")
        if not rd.approved:
            rd = RiskDecision(
                True,
                oid,
                "EXIT",
                "OK_REDUCE_ONLY",
                "failsafe flatten cannot be vetoed",
                self.clock.now(),
            )
        order = self.broker.place_order(intent, rd)
        self.broker.remember(oid, available_ts=self.clock.now(), decision_ts=self.clock.now())
        if order.is_open:
            self.broker._fill(order, float(hint), self.clock.now())

    def exit(self, position: dict[str, Any], reason: str) -> Order:
        """REG-03: always `exit_intent` from the held instrument and whole-lot qty."""
        inst = str(position.get("instrument_id") or "")
        lot = lot_size_for(inst)
        raw_net = int(position.get("net_qty") or 0)
        qty = whole_lots_qty(raw_net, lot)
        if raw_net != qty:
            detail = f"net_qty {raw_net} is not a whole multiple of lot {lot}; closing {qty}"
            _LOG.error("ODD_LOT_FLATTEN %s %s", inst, detail)
            self.bus.publish(
                "HEALTH_ALERT",
                {
                    "reason_code": _ODD_LOT_FLATTEN,
                    "instrument_id": inst,
                    "detail": detail,
                    "severity": "CRITICAL",
                    "ts": self.clock.now().isoformat(),
                },
                source="oms",
            )
        if qty <= 0 or qty > raw_net:
            raise ValueError(f"exit qty {raw_net} has no whole lot <= net (lot {lot})")
        key = inst or str(position.get("symbol") or "")
        live = self.store.positions.get(key)
        live_net = int(live["net_qty"]) if live is not None else qty
        remaining = max(0, live_net - qty)
        # Resize before a partial leaves the book. Flatten keeps the stop until the
        # exit fill lands so a CLOCK-only time stop is never naked; after-fill sync
        # cancels at net_qty == 0.
        if remaining > 0:
            self.sync_protective_stop(live or position, remaining)
        live_after = self.store.positions.get(key)
        live_net_after = int(live_after["net_qty"]) if live_after is not None else 0
        if live_net_after <= 0:
            for order in reversed(list(self.broker.orders.values())):
                if (order.intent.exit_reason or "") == _STOP_RESIZE_FAILED:
                    return order
            raise ValueError("exit qty must be a whole lot")
        qty = min(qty, whole_lots_qty(live_net_after, lot))
        acc = str(position.get("account_id") or "founder")
        parent = str(position.get("entry_order_id") or position.get("position_id") or "x")
        self._exit_seq += 1
        oid = order_id(acc, parent, f"exit{self._exit_seq}")
        hint = position.get("exit_price_hint")
        held = Position(
            symbol=str(position.get("symbol") or (symbol_from_instrument(inst) if inst else "")),
            net_qty=qty,
            avg_price=float(position.get("avg_price") or 0),
            instrument_id=inst,
        )
        raw = exit_intent(
            held,
            exit_reason=reason,
            decision_price=(
                float(hint) if hint is not None else (float(position.get("avg_price") or 0) or None)
            ),
        )
        # exit_intent uses lot_size=1; rewrite to India lot size so lots are whole lots.
        intent = replace(raw, client_order_id=oid, lots=qty // lot, lot_size=lot)
        if inst:
            position["instrument_id"] = inst
        rd = self._approve_reduce_only(intent, "EXIT")
        order = self.broker.place_order(intent, rd)
        self.broker.remember(oid, available_ts=self.clock.now(), decision_ts=self.clock.now())
        return order

    def tighten_stop(self, position_key: str, new_trigger: float) -> None:
        """Trail: move the resting protective stop only toward safety (higher for a long)."""
        oid = self.store.protective.get(position_key)
        if not oid:
            return
        order = self.broker.orders.get(oid)
        if order is None or not order.is_open:
            return
        old = float(order.trigger_price or 0)
        if new_trigger <= old + 1e-9:
            return
        order.trigger_price = new_trigger
        self.broker.remember(oid, trigger_price=new_trigger)

    def cancel_protective(self, position_key: str) -> None:
        live = self.store.positions.get(position_key) or {"instrument_id": position_key}
        self.sync_protective_stop(live, 0)


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
