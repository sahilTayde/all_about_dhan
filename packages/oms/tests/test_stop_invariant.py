"""Protective stop qty tracks net_qty; flatten cancels; race never nets short."""

from __future__ import annotations

from datetime import timedelta

from brokers.factory import make_broker
from brokers.fills import ClockedPaperBroker, ModifyUnsupported, Quote
from brokers.orders import OrderRefused
from contracts.clock import SimClock
from contracts.payloads import Level, Partial, TimeStop
from helpers import INST, NOW, envelope, make_decision, make_exit_plan, make_manager, make_plan

from oms import Account, Veto


class ReplaceOnlyBroker(ClockedPaperBroker):
    """Force cancel-then-replace; optionally reject replacement STOP_HIT places."""

    def __init__(
        self,
        *args: object,
        reject_n: int = 0,
        reject_always: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.reject_n = reject_n
        self.reject_always = reject_always
        self._stop_places = 0
        self.stop_place_oids: list[str] = []

    def modify_order(self, order_id: str, qty: int) -> object:
        raise ModifyUnsupported("test forces cancel-then-replace")

    def place_order(self, intent: object, decision: object) -> object:
        reason = getattr(intent, "exit_reason", None)
        if reason == "STOP_HIT":
            self._stop_places += 1
            self.stop_place_oids.append(str(intent.client_order_id))  # type: ignore[attr-defined]
            if self._stop_places > 1:
                replacements = self._stop_places - 1
                if self.reject_always or replacements <= self.reject_n:
                    raise OrderRefused("injected replacement reject")
        return super().place_order(intent, decision)  # type: ignore[arg-type]


def _fill_entry(router, clock, inst=INST) -> None:
    clock.advance_by(timedelta(milliseconds=250))
    router.broker.on_depth(
        Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=inst)
    )


def _open_stop_orders(broker):
    return [
        o
        for o in broker.orders.values()
        if o.is_open and (o.intent.exit_reason or "") == "STOP_HIT"
    ]


def _stop_qty(broker, key=INST) -> int:
    total = 0
    for o in _open_stop_orders(broker):
        inst = o.intent.instrument_id or o.intent.symbol
        if inst == key:
            total += int(o.intent.lots) * int(o.intent.lot_size or 1)
    return total


def test_stop_qty_equals_net_across_entry_partials_and_founder_close(tmp_path) -> None:
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    plan = make_exit_plan(
        partials=(
            Partial(at=Level(kind="premium", price=155.0), fraction=0.5),
            Partial(at=Level(kind="premium", price=156.0), fraction=0.5),
        ),
    )
    out = pm.router.submit(make_plan(), make_decision(lots=3), Account("founder"), exit_plan=plan)
    assert not isinstance(out, Veto)
    _fill_entry(pm.router, clock)
    assert pm.open_book()[0]["net_qty"] == 195
    assert _stop_qty(pm.router.broker) == 195
    pm.assert_stop_invariant()

    clock.advance_to(NOW.replace(hour=10, minute=20))
    pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 155.00, "ask": 155.20, "ltp": 155.10},
        )
    )
    assert pm.open_book()[0]["net_qty"] == 130
    assert _stop_qty(pm.router.broker) == 130
    pm.assert_stop_invariant()

    clock.advance_by(timedelta(seconds=2))
    pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 156.00, "ask": 156.20, "ltp": 156.10},
        )
    )
    assert pm.open_book()[0]["net_qty"] == 65
    assert _stop_qty(pm.router.broker) == 65
    pm.assert_stop_invariant()

    clock.advance_to(NOW.replace(hour=10, minute=45))
    pm.on_market(
        envelope("FOUNDER_COMMAND", clock.now(), {"kind": "CUT_LOSS", "instrument_id": INST})
    )
    assert pm.open_book() == []
    assert _open_stop_orders(pm.router.broker) == []
    assert _stop_qty(pm.router.broker) == 0
    pm.assert_stop_invariant()


def test_time_stop_flatten_cancels_resting_stop(tmp_path) -> None:
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    plan = make_exit_plan(time_stops=(TimeStop(after_s=180, when="always"),))
    out = pm.router.submit(make_plan(), make_decision(lots=2), Account("founder"), exit_plan=plan)
    assert not isinstance(out, Veto)
    _fill_entry(pm.router, clock)
    assert _stop_qty(pm.router.broker) == 130
    pm.assert_stop_invariant()
    clock.advance_by(timedelta(seconds=181))
    pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 150.00, "ask": 150.20, "ltp": 150.10},
        )
    )
    assert pm.open_book() == []
    assert _open_stop_orders(pm.router.broker) == []
    pm.assert_stop_invariant()


def test_stop_fill_itself_leaves_no_resting_stop(tmp_path) -> None:
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    out = pm.router.submit(
        make_plan(), make_decision(lots=3), Account("founder"), exit_plan=make_exit_plan()
    )
    assert not isinstance(out, Veto)
    _fill_entry(pm.router, clock)
    assert _stop_qty(pm.router.broker) == 195
    clock.advance_by(timedelta(seconds=1))
    # Catastrophic is 140. A print through the trigger fills the SL-M.
    pm.router.broker.on_depth(
        Quote(available_ts=clock.now(), bid=139.00, ask=139.20, ltp=139.10, instrument_id=INST)
    )
    assert pm.open_book() == []
    assert _open_stop_orders(pm.router.broker) == []
    assert int(pm.store.closed[-1]["net_qty"]) == 0
    pm.assert_stop_invariant()


def test_stop_fill_racing_partial_never_nets_short(tmp_path) -> None:
    clock = SimClock(NOW)
    pm = make_manager(tmp_path, clock, broker=make_broker(clock=clock))
    out = pm.router.submit(
        make_plan(), make_decision(lots=3), Account("founder"), exit_plan=make_exit_plan()
    )
    assert not isinstance(out, Veto)
    _fill_entry(pm.router, clock)
    book = pm.open_book()[0]
    assert book["net_qty"] == 195
    assert _stop_qty(pm.router.broker) == 195

    work = dict(book)
    work["net_qty"] = 65
    work["exit_price_hint"] = 155.00
    work["exit_reason"] = "PARTIAL"
    exit_order = pm.router.exit(work, "PARTIAL")
    # Pre-sync: remaining 130, old 195-lot stop cancelled, never both live.
    assert _stop_qty(pm.router.broker) == 130
    assert all(
        int(o.intent.lots) * int(o.intent.lot_size or 1) <= 130
        for o in _open_stop_orders(pm.router.broker)
    )

    stops = _open_stop_orders(pm.router.broker)
    assert len(stops) == 1
    pm.router.broker._fill(stops[0], 140.00, clock.now())
    net_after_stop = int((pm.store.positions.get(INST) or {}).get("net_qty") or 0)
    assert net_after_stop >= 0
    assert net_after_stop == 65

    if exit_order.is_open:
        pm.router.broker._fill(exit_order, 155.00, clock.now())
    net = int((pm.store.positions.get(INST) or {}).get("net_qty") or 0)
    assert net >= 0
    assert pm.open_book() == []
    assert _open_stop_orders(pm.router.broker) == []
    pm.assert_stop_invariant()


def _open_three_lots(tmp_path, clock, broker):
    pm = make_manager(tmp_path, clock, broker=broker)
    out = pm.router.submit(
        make_plan(),
        make_decision(lots=3),
        Account("founder"),
        exit_plan=make_exit_plan(
            partials=(Partial(at=Level(kind="premium", price=155.0), fraction=0.5),)
        ),
    )
    assert not isinstance(out, Veto)
    _fill_entry(pm.router, clock)
    assert pm.open_book()[0]["net_qty"] == 195
    assert _stop_qty(pm.router.broker) == 195
    pm.assert_stop_invariant()
    return pm


def _partial_at_155(pm, clock) -> None:
    clock.advance_to(NOW.replace(hour=10, minute=20))
    pm.on_market(
        envelope(
            "DEPTH_QUOTE",
            clock.now(),
            {"instrument_id": INST, "bid": 155.00, "ask": 155.20, "ltp": 155.10},
        )
    )


def test_replace_rejected_once_then_succeeds(tmp_path) -> None:
    clock = SimClock(NOW)
    broker = ReplaceOnlyBroker(clock=clock, reject_n=1)
    pm = _open_three_lots(tmp_path, clock, broker)
    first_id = _open_stop_orders(broker)[0].client_order_id
    _partial_at_155(pm, clock)
    assert int((pm.store.positions.get(INST) or {}).get("net_qty") or 0) >= 0
    stops = _open_stop_orders(broker)
    assert len(stops) == 1
    assert _stop_qty(broker) == 130
    assert pm.open_book()[0]["net_qty"] == 130
    assert stops[0].client_order_id != first_id
    replace_oids = broker.stop_place_oids[1:]
    assert replace_oids
    assert len(set(replace_oids)) == 1
    pm.assert_stop_invariant()


def test_replace_rejected_always_flattens_and_alerts(tmp_path) -> None:
    clock = SimClock(NOW)
    broker = ReplaceOnlyBroker(clock=clock, reject_always=True)
    pm = _open_three_lots(tmp_path, clock, broker)
    _partial_at_155(pm, clock)
    net = int((pm.store.positions.get(INST) or {}).get("net_qty") or 0)
    assert net >= 0
    assert net == 0
    assert pm.open_book() == []
    assert _open_stop_orders(broker) == []
    assert _stop_qty(broker) == 0
    assert any(
        a.get("severity") == "CRITICAL" and a.get("reason_code") == "STOP_RESIZE_FAILED"
        for a in pm.alerts
    )
    pm.assert_stop_invariant()


def test_modify_path_keeps_same_order_id_qty_195_then_130(tmp_path) -> None:
    clock = SimClock(NOW)
    pm = _open_three_lots(tmp_path, clock, make_broker(clock=clock))
    first = _open_stop_orders(pm.router.broker)[0]
    first_id = first.client_order_id
    assert int(first.intent.lots) * int(first.intent.lot_size or 1) == 195
    _partial_at_155(pm, clock)
    after = _open_stop_orders(pm.router.broker)
    assert len(after) == 1
    assert after[0].client_order_id == first_id
    assert _stop_qty(pm.router.broker) == 130
    assert pm.open_book()[0]["net_qty"] == 130
    pm.assert_stop_invariant()
