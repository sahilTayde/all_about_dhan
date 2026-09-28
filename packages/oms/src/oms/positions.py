"""V2-09 position manager: book + exit loop. Paper only. No durable rehydrate (V2-10)."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any

from brokers.fills import Quote
from brokers.orders import Position, exit_intent
from contracts.envelope import Envelope
from contracts.instruments import India
from contracts.payloads import ExitPlan, PositionClosed, PositionUpdate
from events.bus import MemoryBus

from oms.exits import (
    ALLOWED_REASONS,
    SEND_ON_CLOCK,
    STALE_EXEMPT,
    STALE_MAX_AGE_S,
    ExitRequest,
    as_ist,
    assert_exit_reason,
    choose_time_stop,
    evaluate,
    freeze_fill_levels,
    instrument_lot_size,
    option_side,
    plan_as_json,
    plan_from_mapping,
    quote_is_stale,
    whole_lots_qty,
)
from oms.ledger_stub import MemoryLedger
from oms.router import OrderRouter, symbol_from_instrument

_INDIA = India()
_LOG = logging.getLogger(__name__)


def _expiry_of(instrument_id: str) -> datetime | None:
    raw = _INDIA.parse_instrument_id(instrument_id).get("expiry") or ""
    if not raw:
        return None
    return datetime.fromisoformat(f"{raw}T00:00:00+05:30")


def _key(pos: dict[str, Any]) -> str:
    return str(pos.get("instrument_id") or pos.get("symbol") or "")


class PositionManager:
    """Owns the open book after the entry fill. Exits come only from the position record."""

    def __init__(
        self,
        *,
        clock: Any,
        router: OrderRouter,
        store: MemoryLedger | None = None,
        bus: MemoryBus | None = None,
        quote_max_age_s: float = STALE_MAX_AGE_S,
    ) -> None:
        self.clock = clock
        self.router = router
        self.store = store if store is not None else router.store
        self.bus = bus if bus is not None else router.bus
        self.quote_max_age_s = quote_max_age_s
        self.kill_switch = False
        self.alerts: list[dict[str, Any]] = []
        self._pending: dict[str, ExitRequest] = {}
        self._plans: dict[str, ExitPlan] = {}
        self._fill_ctx: dict[str, dict[str, float]] = {}
        self.router.positions = self

    def remember_plan(self, client_order_id: str, plan: ExitPlan) -> None:
        plan_from_mapping(plan_as_json(plan))  # refuse a plan without catastrophic
        self._plans[client_order_id] = plan

    def remember_fill_context(
        self,
        client_order_id: str,
        *,
        entry_underlying: float | None = None,
        atr14: float | None = None,
    ) -> None:
        ctx: dict[str, float] = {}
        if entry_underlying is not None:
            ctx["entry_underlying"] = float(entry_underlying)
        if atr14 is not None:
            ctx["atr14"] = float(atr14)
        self._fill_ctx[client_order_id] = ctx

    def on_fill(
        self,
        *,
        client_order_id: str,
        qty: int,
        price: float,
        side: str,
        instrument_id: str,
        symbol: str,
        account_id: str,
        strategy_id: str = "",
        entry_order_id: str = "",
        exit_plan: ExitPlan | None = None,
    ) -> None:
        now = self.clock.now()
        key = instrument_id or symbol
        row = self.store.positions.get(key)
        plan = (
            exit_plan or self._plans.get(client_order_id) or self._plans.get(entry_order_id or "")
        )
        if side == "BUY" and row is not None:
            if plan is None and row.get("exit_plan_json"):
                plan = plan_from_mapping(row["exit_plan_json"])
            if plan is None:
                raise ValueError("entry fill has no ExitPlan (catastrophic required)")
            fill_ts = row.get("fill_ts") or now
            chosen = choose_time_stop(plan, fill_ts, _expiry_of(instrument_id))
            row["exit_plan"] = plan
            row["exit_plan_json"] = plan_as_json(plan)
            row["chosen_time_stop"] = chosen
            row["fill_ts"] = fill_ts
            row["account_id"] = account_id or row.get("account_id") or "founder"
            row["strategy_id"] = strategy_id or row.get("strategy_id") or ""
            row["orig_qty"] = int(row["net_qty"])
            ctx = self._fill_ctx.get(client_order_id) or self._fill_ctx.get(entry_order_id or "")
            freeze_fill_levels(
                row,
                plan,
                price,
                int(row["net_qty"]),
                entry_underlying=(ctx or {}).get("entry_underlying"),
                atr14=(ctx or {}).get("atr14"),
            )
            row["position_id"] = row.get("position_id") or client_order_id
            row["entry_order_id"] = row.get("entry_order_id") or client_order_id
            row["last_good_quote"] = price
            row["last_good_ts"] = now
            row["mark"] = price
            row["partials_done"] = int(row.get("partials_done") or 0)
            self._publish_update(row)
        elif side == "SELL":
            closed = self.store.closed[-1] if self.store.closed else row
            if closed:
                self._publish_closed(closed, client_order_id)

    def on_market(self, env: Envelope) -> list[ExitRequest]:
        available = as_ist(env.available_ts)
        if available > self.clock.now():
            return []  # no look-ahead
        payload = env.payload or {}
        fired: list[ExitRequest] = []
        founder: str | None = None
        strategy_exit = False
        kind = env.event_type
        if kind == "FOUNDER_COMMAND":
            founder = str(payload.get("kind") or "")
            if founder == "KILL":
                self.kill_switch = True
        elif kind == "STRATEGY_EXIT":
            strategy_exit = True
        self._ingest_quote(kind, payload, available)
        target = str(payload.get("instrument_id") or payload.get("position_id") or "")
        for pos in list(self.store.open_positions()):
            ids = (pos.get("instrument_id"), pos.get("position_id"), pos.get("symbol"))
            quote_kinds = ("TICK", "DEPTH_QUOTE", "QUOTE_SNAPSHOT", "BAR_CLOSED")
            skip_other = target and target not in ids and kind in quote_kinds
            if skip_other and not (kind == "BAR_CLOSED" and _same_underlying(target, pos)):
                continue
            if "exit_plan" not in pos:
                raw = pos.get("exit_plan_json")
                if raw:
                    pos["exit_plan"] = plan_from_mapping(raw)
                else:
                    continue
            if pos.get("exit_in_flight") and not (
                self._pending.get(_key(pos))
                and not quote_is_stale(
                    pos.get("last_good_ts"), self.clock.now(), self.quote_max_age_s
                )
            ):
                continue
            own_opp, boss_opp = _flip_flags(kind, payload, pos)
            req = evaluate(
                pos,
                self.clock.now(),
                mark=(
                    pos.get("mark")
                    if pos.get("mark") == pos.get("mark")
                    else pos.get("last_good_quote")
                ),
                quote_ts=pos.get("last_good_ts"),
                kill=self.kill_switch,
                founder_kind=founder,
                strategy_exit=strategy_exit,
                quote_max_age_s=self.quote_max_age_s,
                event_kind=kind,
                underlying=_underlying_px(kind, payload, pos),
                own_opposite=own_opp,
                boss_opposite=boss_opp,
            )
            if req is None:
                pending = self._pending.get(_key(pos))
                if pending is not None and not quote_is_stale(
                    pos.get("last_good_ts"), self.clock.now(), self.quote_max_age_s
                ):
                    req = pending
            if req is None:
                continue
            try:
                assert_exit_reason(req, pos["exit_plan"])
            except RuntimeError as exc:
                _LOG.critical("REG-18a: %s; flattening anyway", exc)
                self._alert(
                    "REG_18A_MISMATCH",
                    _key(pos),
                    str(exc),
                    severity="CRITICAL",
                )
            try:
                applied = self._apply(pos, req)
            except Exception as exc:
                _LOG.critical("exit apply failed; failsafe flatten: %s", exc)
                self._alert("EXIT_APPLY_FAILED", _key(pos), str(exc), severity="CRITICAL")
                inst = str(pos.get("instrument_id") or "")
                qty = whole_lots_qty(int(pos.get("net_qty") or 0), instrument_lot_size(inst))
                if qty <= 0:
                    continue
                applied = self._apply(
                    pos,
                    ExitRequest(
                        "FAILSAFE_MTM",
                        "mark",
                        qty,
                        stale_quote=True,
                        price_hint=pos.get("last_good_quote"),
                    ),
                )
            if applied is not None:
                fired.append(applied)
        self.assert_stop_invariant()
        return fired

    def mark_to_market(self, instrument_id: str, price: float, ts: datetime | None = None) -> None:
        """Fail-safe: an exception closes at the last good quote and blocks entries (REG-05d)."""
        try:
            if price is None or price != price or price < 0:
                raise ValueError("invalid mark")
            self._set_mark(instrument_id, price, ts or self.clock.now())
        except Exception:
            self._failsafe_mtm()

    def request_strategy_exit(self, instrument_id: str) -> list[ExitRequest]:
        iso = self.clock.now().isoformat()
        return self.on_market(
            Envelope(
                v=2,
                event_type="STRATEGY_EXIT",
                event_id="sx",
                stream="oms",
                source="strategy",
                event_ts=iso,
                available_ts=iso,
                timestamp=iso,
                account_id="founder",
                correlation_id=None,
                causation_id=None,
                payload={"instrument_id": instrument_id},
            )
        )

    def assert_stop_invariant(self) -> None:
        """sum(open STOP_HIT qty) == net_qty for every name; 0 open stops when flat."""
        open_keys: set[str] = set()
        for pos in self.store.open_positions():
            key = _key(pos)
            open_keys.add(key)
            net = int(pos.get("net_qty") or 0)
            stop_qty = self.router.open_stop_qty(key)
            if stop_qty != net:
                raise RuntimeError(f"REG-02: open stop qty {stop_qty} != net_qty {net} for {key}")
            if net > 0 and not self.store.has_protective(key):
                raise RuntimeError(f"REG-02: open position {key} has no protective stop")
            stop_oid = self.store.protective.get(key)
            held = self.router.broker.orders.get(stop_oid) if stop_oid else None
            if held is None or not held.is_open:
                raise RuntimeError(f"REG-02: protective stop {stop_oid} is not resting")
        for order in list(self.router.broker.orders.values()):
            if not order.is_open:
                continue
            if order.intent.purpose != "EXIT" or (order.intent.exit_reason or "") != "STOP_HIT":
                continue
            key = order.intent.instrument_id or order.intent.symbol
            if key not in open_keys:
                raise RuntimeError(
                    f"REG-02: leftover open stop {order.client_order_id} for flat {key}"
                )

    def open_book(self) -> list[dict[str, Any]]:
        return self.store.open_positions()

    def _ingest_quote(self, kind: str, payload: dict[str, Any], available: datetime) -> None:
        inst = str(payload.get("instrument_id") or "")
        mark = payload.get("ltp")
        if mark is None:
            mark = (
                payload.get("c")
                if kind == "BAR_CLOSED"
                else payload.get("bid") or payload.get("ask")
            )
        bid = payload.get("bid")
        ask = payload.get("ask")
        if inst and mark is not None:
            quote = Quote(
                available_ts=available,
                bid=float(bid) if bid is not None else None,
                ask=float(ask) if ask is not None else None,
                ltp=float(mark),
                instrument_id=inst,
            )
            if available <= self.clock.now():
                self._fill_clock_exits(quote)
                self.router.broker.on_depth(quote)
        if mark is None or not inst:
            return
        try:
            self._set_mark(inst, float(mark), available)
        except Exception:
            self._failsafe_mtm()

    def _fill_clock_exits(self, quote: Quote) -> None:
        """Time-stop / pending MARKET exits fill at the first post-deadline depth bid."""
        for order in list(self.router.broker.orders.values()):
            if not order.is_open or order.intent.purpose != "EXIT":
                continue
            if order.intent.exit_reason != "TIME_EXIT":
                continue
            same = quote.instrument_id == order.intent.instrument_id
            if quote.instrument_id and order.intent.instrument_id and not same:
                continue
            px = quote.bid if quote.bid is not None else quote.ltp
            if px is None:
                continue
            self.router.broker._fill(order, float(px), quote.available_ts)
            self.router.broker.fill_models[order.client_order_id] = "depth"

    def _set_mark(self, instrument_id: str, price: float, ts: datetime) -> None:
        if price != price or price < 0:
            raise ValueError("invalid mark")
        row = self.store.positions.get(instrument_id)
        if row is None:
            return
        row["mark"] = price
        row["last_good_quote"] = price
        row["last_good_ts"] = ts
        row["updated_at"] = self.clock.now()
        self._publish_update(row)

    def _apply(self, pos: dict[str, Any], req: ExitRequest) -> ExitRequest | None:
        if req.reason not in ALLOWED_REASONS:
            raise RuntimeError(f"illegal exit reason {req.reason}")
        key = _key(pos)
        stale = quote_is_stale(pos.get("last_good_ts"), self.clock.now(), self.quote_max_age_s)
        if stale and req.reason not in STALE_EXEMPT and req.reason not in SEND_ON_CLOCK:
            self._pending[key] = req
            return None
        self._pending.pop(key, None)
        if req.reason == "TRAIL_STOP" and req.new_stop is not None:
            self.router.tighten_stop(key, req.new_stop)
            pos["stop_price"] = float(req.new_stop)
            return req
        work = dict(pos)
        work["net_qty"] = req.qty
        inst = str(work.get("instrument_id") or "")
        work["symbol"] = work.get("symbol") or symbol_from_instrument(inst)
        hint = req.price_hint if req.price_hint is not None else work.get("last_good_quote")
        work["exit_price_hint"] = hint
        work["exit_reason"] = req.reason
        pos["exit_in_flight"] = True
        pos["exit_reason"] = req.reason
        live_net = int(pos.get("net_qty") or 0)
        flatten_now = req.qty >= live_net
        time_due = False
        if req.reason == "TIME_EXIT":
            chosen = pos.get("chosen_time_stop")
            fill_ts = pos.get("fill_ts")
            last_ts = pos.get("last_good_ts")
            deadline = None
            if chosen and fill_ts:
                deadline = as_ist(fill_ts) + timedelta(seconds=int(chosen.after_s))
            time_due = bool(
                deadline is not None and last_ts is not None and as_ist(last_ts) >= deadline
            )
        will_fill = time_due or (
            req.reason != "TIME_EXIT" and (req.reason in STALE_EXEMPT or not stale)
        )
        order = self.router.exit(work, req.reason)
        # Same-step flatten fill: drop the SL-M first so on_depth cannot oversell.
        if flatten_now and will_fill:
            self.router.sync_protective_stop(pos, 0)
        if req.reason == "TIME_EXIT":
            if time_due:
                self._try_fill_exit(order, work, req, force_hint=False)
        elif req.reason in STALE_EXEMPT:
            self._try_fill_exit(order, work, req, force_hint=True)
        elif not stale:
            self._try_fill_exit(order, work, req, force_hint=False)
        if req.reason == "TRAIL_STOP":
            pos["exit_in_flight"] = False
        elif req.reason == "PARTIAL" and key in self.store.positions:
            self.store.positions[key]["exit_in_flight"] = False
            self.store.positions[key]["partials_done"] = int(pos.get("partials_done") or 0) + 1
        if req.stale_quote or (stale and req.reason in STALE_EXEMPT):
            self._alert("STALE_QUOTE", key, req.reason)
        return req

    def _try_fill_exit(
        self, order: Any, pos: dict[str, Any], req: ExitRequest, *, force_hint: bool
    ) -> None:
        inst = str(pos.get("instrument_id") or "")
        px = req.price_hint if req.price_hint is not None else pos.get("last_good_quote")
        if px is None or not getattr(order, "is_open", False):
            return
        if force_hint:
            # EOD / founder / kill / failsafe: last good print, not a later fill-model path.
            self.router.broker._fill(order, float(px), self.clock.now())
            self.router.broker.fill_models[order.client_order_id] = "stale_last_good"
            return
        quote = Quote(
            available_ts=self.clock.now(),
            bid=float(px),
            ask=round(float(px) + 0.20, 2),
            ltp=float(px),
            instrument_id=inst,
        )
        self.router.broker.on_depth(quote)

    def _failsafe_mtm(self) -> None:
        now = self.clock.now()
        self.store.recon_ok = False
        self.store.session_halts.append(
            {
                "session": now.date().isoformat(),
                "account_id": "founder",
                "halt_ts": now.isoformat(),
                "kind": "FAILSAFE_MTM",
                "forced_closes_json": "[]",
                "created_at": now.isoformat(),
            }
        )
        self._alert("FAILSAFE_MTM", "*", "raising mark")
        for pos in list(self.store.open_positions()):
            inst = str(pos.get("instrument_id") or "")
            qty = whole_lots_qty(int(pos["net_qty"]), instrument_lot_size(inst))
            if qty <= 0:
                continue
            hint = pos.get("last_good_quote")
            self._apply(
                pos,
                ExitRequest("FAILSAFE_MTM", "mark", qty, stale_quote=True, price_hint=hint),
            )

    def _alert(
        self, code: str, instrument_id: str, detail: str, *, severity: str = "WARNING"
    ) -> None:
        rec = {
            "reason_code": code,
            "instrument_id": instrument_id,
            "detail": detail,
            "severity": severity,
            "ts": self.clock.now().isoformat(),
        }
        self.alerts.append(rec)
        self.bus.publish("HEALTH_ALERT", rec, source="oms")

    def _publish_update(self, pos: dict[str, Any]) -> None:
        mark = float(pos.get("mark") or pos.get("avg_price") or 0)
        qty = int(pos.get("net_qty") or 0)
        avg = float(pos.get("avg_price") or 0)
        payload = PositionUpdate(
            position_id=str(pos.get("position_id") or ""),
            account_id=str(pos.get("account_id") or "founder"),
            instrument_id=str(pos.get("instrument_id") or ""),
            net_qty=qty,
            avg_price=avg,
            mark=mark,
            unrealized_inr=round((mark - avg) * qty, 2),
            stop={"kind": "premium", "price": float(pos.get("stop_price") or 0)},
            protective_order=self.store.protective.get(_key(pos)),
            strategy_id=str(pos.get("strategy_id") or ""),
        )
        self.bus.publish(
            "POSITION_UPDATE",
            {
                "position_id": payload.position_id,
                "account_id": payload.account_id,
                "instrument_id": payload.instrument_id,
                "net_qty": payload.net_qty,
                "avg_price": payload.avg_price,
                "mark": payload.mark,
                "unrealized_inr": payload.unrealized_inr,
                "stop": payload.stop,
                "protective_order": payload.protective_order,
                "strategy_id": payload.strategy_id,
            },
            source="oms",
        )

    def _publish_closed(self, pos: dict[str, Any], exit_oid: str) -> None:
        qty = abs(int(pos.get("last_exit_qty") or pos.get("orig_qty") or 0))
        exit_px = float(pos.get("last_exit_price") or 0)
        avg = float(pos.get("avg_price") or 0)
        if qty:
            gross = round((exit_px - avg) * qty, 2)
        else:
            gross = round(float(pos.get("realized_pnl") or 0), 2)
        ids = {pos.get("entry_order_id"), exit_oid}
        charges = sum(
            c.components.get("total", 0.0) for c in self.store.charges if c.client_order_id in ids
        )
        opened = pos.get("opened_at") or pos.get("fill_ts")
        held = 0
        if isinstance(opened, datetime):
            held = int((self.clock.now() - as_ist(opened)).total_seconds())
        payload = PositionClosed(
            position_id=str(pos.get("position_id") or ""),
            exit_reason=str(pos.get("exit_reason") or "UNKNOWN"),
            gross_inr=gross,
            charges_inr=round(float(charges), 2),
            net_inr=round(gross - float(charges), 2),
            held_s=held,
            trade_id=exit_oid,
        )
        self.bus.publish(
            "POSITION_CLOSED",
            {
                "position_id": payload.position_id,
                "exit_reason": payload.exit_reason,
                "gross_inr": payload.gross_inr,
                "charges_inr": payload.charges_inr,
                "net_inr": payload.net_inr,
                "held_s": payload.held_s,
                "trade_id": payload.trade_id,
            },
            source="oms",
        )


def _same_underlying(target: str, pos: dict[str, Any]) -> bool:
    inst = str(pos.get("instrument_id") or "")
    try:
        pos_sym = str(_INDIA.parse_instrument_id(inst).get("symbol") or "")
        tgt_sym = str(_INDIA.parse_instrument_id(target).get("symbol") or "")
    except ValueError:
        return False
    return bool(pos_sym and pos_sym == tgt_sym)


def _underlying_px(kind: str, payload: dict[str, Any], pos: dict[str, Any]) -> float | None:
    for key in ("spot", "underlying_ltp", "underlying_close"):
        raw = payload.get(key)
        if isinstance(raw, (int, float)) and raw == raw:
            return float(raw)
    raw_under = payload.get("underlying")
    if isinstance(raw_under, (int, float)) and raw_under == raw_under:
        return float(raw_under)
    inst = str(payload.get("instrument_id") or "")
    if kind == "BAR_CLOSED" and inst and _same_underlying(inst, pos) and "FNO" not in inst:
        close = payload.get("c", payload.get("close"))
        if close is not None:
            return float(close)
    held = pos.get("entry_underlying")
    return float(held) if held is not None else None


def _flip_flags(kind: str, payload: dict[str, Any], pos: dict[str, Any]) -> tuple[bool, bool]:
    own = payload.get("own_opposite") is True
    boss = payload.get("boss_opposite") is True
    side = option_side(str(pos.get("instrument_id") or ""))
    other = str(payload.get("side") or "")
    if other not in {"CE", "PE"}:
        inst = str(payload.get("instrument_id") or "")
        if inst:
            try:
                other = option_side(inst)
            except ValueError:
                other = ""
    opposite = bool(other and other != side)
    if kind == "SIGNAL" and opposite:
        strat = str(payload.get("strategy_id") or "")
        if strat and strat == str(pos.get("strategy_id") or ""):
            own = True
    if (
        kind in {"DECISION", "BOSS_DECISION"}
        and opposite
        and str(payload.get("decision") or "ENTER") == "ENTER"
    ):
        under = str(payload.get("underlying") or "")
        inst = str(pos.get("instrument_id") or "")
        pos_under = str(_INDIA.parse_instrument_id(inst).get("symbol") or "")
        if not under or under == pos_under:
            boss = True
    return own, boss


def held_position(row: dict[str, Any]) -> Position:
    """REG-03: exit is built from the held record, never a recomputed strike."""
    inst = str(row.get("instrument_id") or "")
    lot = instrument_lot_size(inst)
    qty = whole_lots_qty(int(row.get("net_qty") or 0), lot)
    return Position(
        symbol=str(row.get("symbol") or symbol_from_instrument(inst)),
        net_qty=qty,
        avg_price=float(row.get("avg_price") or 0),
        instrument_id=inst,
    )


def exit_from_held(row: dict[str, Any], reason: str) -> Any:
    held = held_position(row)
    lot = instrument_lot_size(held.instrument_id)
    raw = exit_intent(
        held,
        exit_reason=reason,
        decision_price=row.get("exit_price_hint"),
    )
    return replace(raw, lots=held.net_qty // lot, lot_size=lot)


__all__ = [
    "PositionManager",
    "exit_from_held",
    "held_position",
]
