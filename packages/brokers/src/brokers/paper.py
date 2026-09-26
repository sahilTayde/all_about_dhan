"""PaperBroker: simulated fills on the next tick, configurable slippage. Never calls a broker."""

from __future__ import annotations

import logging
from typing import Any, Optional

from brokers.orders import (
    BrokerAdapter,
    InvalidTransition,
    Order,
    OrderSnapshot,
    OrderState,
    Position,
    exit_intent,
)
from risk_engine import RiskDecision, TradeIntent

log = logging.getLogger("brokers.paper")


class PaperBroker(BrokerAdapter):
    """Orders placed now are first looked at on the next `on_tick` for their symbol.

    MARKET fills at LTP ± slippage. LIMIT fills when LTP crosses the limit, at no worse than the
    limit. SL-M becomes MARKET once LTP touches the trigger; SL becomes LIMIT. A super order's
    target (LIMIT) and stop (SL-M, optionally trailing) legs appear after the entry fills; when
    one leg fills the other is cancelled (OCO).
    """

    name = "paper"
    mode = "paper"

    def __init__(self, *, slippage_ticks: int = 1, tick_size: float = 0.05, starting_cash: float = 0.0) -> None:
        super().__init__()
        self.tick_size = tick_size
        self.slippage = slippage_ticks * tick_size
        self.cash = starting_cash
        self.ltp: dict[str, float] = {}
        self._positions: dict[str, Position] = {}
        self._legs: dict[str, tuple[str, str]] = {}  # super entry id -> (target leg id, stop leg id)
        self._trail_ref: dict[str, float] = {}  # stop leg id -> price the trail last stepped from
        self._triggered: set[str] = set()

    # ------------------------------------------------------------- orders

    def place_order(self, intent: TradeIntent, decision: RiskDecision) -> Order:
        self.require_approval(decision, self.action_for(intent), intent.client_order_id)
        return self._accept(intent)

    def place_super_order(self, intent: TradeIntent, decision: RiskDecision) -> Order:
        if intent.target is None or intent.stop_loss is None:
            raise ValueError("super order needs target and stop_loss")
        self.require_approval(decision, "ENTRY", intent.client_order_id)
        return self._accept(intent, is_super=True)

    def _accept(self, intent: TradeIntent, **kw: Any) -> Order:
        if intent.client_order_id in self.orders:  # idempotent retry
            return self.orders[intent.client_order_id]
        order = self._register(intent, **kw)
        order.transition(OrderState.SUBMITTED, "paper: fills on next tick")
        return order

    def modify_order(
        self, order: Order, decision: RiskDecision, *, price: Optional[float] = None,
        trigger_price: Optional[float] = None, target: Optional[float] = None,
        stop_loss: Optional[float] = None, trailing_jump: Optional[float] = None,
    ) -> Order:
        self.require_approval(decision, "MODIFY", order.client_order_id)
        legs = self._legs.get(order.client_order_id)
        if not order.is_open and not legs:
            raise InvalidTransition(f"{order.client_order_id}: cannot modify a {order.state.value} order")
        for name, value in (("price", price), ("trigger_price", trigger_price), ("target", target),
                            ("stop_loss", stop_loss), ("trailing_jump", trailing_jump)):
            if value is not None:
                setattr(order, name, value)
        if legs:
            tgt, stop = self.orders[legs[0]], self.orders[legs[1]]
            if target is not None:
                tgt.price = target
            if stop_loss is not None:
                stop.trigger_price = stop_loss
            if trailing_jump is not None:
                stop.trailing_jump = trailing_jump
        log.info("paper modify %s price=%s trigger=%s target=%s stop=%s trail=%s", order.client_order_id,
                 price, trigger_price, target, stop_loss, trailing_jump)
        return order

    def cancel_order(self, order: Order, decision: RiskDecision, reason: str = "USER_CANCEL") -> Order:
        self.require_approval(decision, "CANCEL", order.client_order_id)
        if order.is_open:
            self._cancel(order, reason)
        for leg in self._legs.pop(order.client_order_id, ()):
            if self.orders[leg].is_open:
                self._cancel(self.orders[leg], reason)
        return order

    def _cancel(self, order: Order, reason: str) -> None:
        order.cancel_reason = reason
        order.transition(OrderState.CANCELLED, reason)

    def flatten_all(self, decision: RiskDecision) -> list[Order]:
        self.require_approval(decision, "FLATTEN", "FLATTEN_ALL")
        for order in list(self.orders.values()):
            if order.is_open:
                self._cancel(order, "KILL_SWITCH")
        self._legs.clear()
        return [
            self._accept(exit_intent(p, exit_reason="KILL_SWITCH", decision_price=self.ltp.get(p.symbol)))
            for p in self.get_positions()
        ]

    # --------------------------------------------------------------- ticks

    def on_tick(self, symbol: str, ltp: float, ts: Any = None) -> None:
        self.ltp[symbol] = ltp
        for order in [o for o in self.orders.values() if o.is_open and o.intent.symbol == symbol]:
            if not order.is_open:  # cancelled by an OCO sibling earlier in this loop
                continue
            self._trail(order, ltp)
            px = self._fill_price(order, ltp)
            if px is not None:
                self._fill(order, px, ts)

    def _tick(self, x: float) -> float:
        return max(self.tick_size, round(round(x / self.tick_size) * self.tick_size, 2))

    def _fill_price(self, order: Order, ltp: float) -> Optional[float]:
        buy = order.intent.side == "BUY"
        slip = self.slippage if buy else -self.slippage
        kind = order.intent.order_type
        if kind == "MARKET":
            return self._tick(ltp + slip)
        if kind in ("SL", "SL-M") and order.client_order_id not in self._triggered:
            if not (ltp >= order.trigger_price if buy else ltp <= order.trigger_price):
                return None
            self._triggered.add(order.client_order_id)
        if kind == "SL-M":
            return self._tick(ltp + slip)
        if buy and ltp <= order.price:
            return self._tick(min(order.price, ltp + slip))
        if not buy and ltp >= order.price:
            return self._tick(max(order.price, ltp + slip))
        return None

    def _trail(self, order: Order, ltp: float) -> None:
        ref = self._trail_ref.get(order.client_order_id)
        if not order.trailing_jump or ref is None:
            return
        protects_long = order.intent.side == "SELL"
        steps = int(((ltp - ref) if protects_long else (ref - ltp)) // order.trailing_jump)
        if steps > 0:
            move = steps * order.trailing_jump * (1 if protects_long else -1)
            order.trigger_price = self._tick(order.trigger_price + move)
            self._trail_ref[order.client_order_id] = ref + move
            log.info("paper trail %s stop -> %s", order.client_order_id, order.trigger_price)

    def _fill(self, order: Order, px: float, ts: Any) -> None:
        qty = order.remaining_qty
        order.apply_fill(qty, px, ts)
        i = order.intent
        signed = qty if i.side == "BUY" else -qty
        pos = self._positions.get(i.symbol) or Position(i.symbol, 0, 0.0, i.instrument_id)
        new_net = pos.net_qty + signed
        if new_net == 0:
            self._positions.pop(i.symbol, None)
        else:
            if pos.net_qty == 0 or (pos.net_qty > 0) != (new_net > 0):
                pos.avg_price = px
            elif (pos.net_qty > 0) == (signed > 0):
                pos.avg_price = round((pos.avg_price * abs(pos.net_qty) + px * qty) / abs(new_net), 4)
            pos.net_qty = new_net
            self._positions[i.symbol] = pos
        self.cash -= signed * px
        if order.is_super:
            self._open_legs(order)
        for parent, legs in list(self._legs.items()):
            if order.client_order_id in legs:
                for leg in legs:
                    if self.orders[leg].is_open:
                        self._cancel(self.orders[leg], "OCO_SIBLING_FILLED")
                del self._legs[parent]

    def _open_legs(self, parent: Order) -> None:
        i = parent.intent
        common = dict(
            symbol=i.symbol, side="SELL" if i.side == "BUY" else "BUY", lots=i.lots, lot_size=i.lot_size,
            purpose="EXIT", instrument_id=i.instrument_id, exchange=i.exchange, product_type=i.product_type,
            trade_id=i.trade_id,
        )
        tgt = self._accept(TradeIntent(order_type="LIMIT", price=parent.target, decision_price=parent.target,
                                       exit_reason="TARGET_HIT", client_order_id=f"{i.client_order_id}-T", **common))
        stop = self._accept(
            TradeIntent(order_type="SL-M", trigger_price=parent.stop_loss, decision_price=parent.stop_loss,
                        exit_reason="STOP_HIT", client_order_id=f"{i.client_order_id}-S", **common),
            trailing_jump=parent.trailing_jump,
        )
        self._legs[i.client_order_id] = (tgt.client_order_id, stop.client_order_id)
        self._trail_ref[stop.client_order_id] = parent.avg_fill_price

    # --------------------------------------------------------------- reads

    def get_order_status(self, order: Order) -> Order:
        return order

    def get_positions(self) -> list[Position]:
        return [Position(p.symbol, p.net_qty, p.avg_price, p.instrument_id) for p in self._positions.values()]

    def get_orders(self) -> list[OrderSnapshot]:
        return [
            OrderSnapshot(o.client_order_id, o.client_order_id, o.state, o.filled_qty, o.intent.symbol)
            for o in self.orders.values()
        ]

    def get_balance(self) -> float:
        return round(self.cash, 2)
