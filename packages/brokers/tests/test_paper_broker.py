"""PaperBroker: approval required, next-tick fills, slippage, super order legs, flatten."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

from brokers import InvalidTransition, OrderRefused, OrderState, PaperBroker, attach_ledger
from ledger import Ledger, load_rates
from risk_engine import IST, RiskDecision, RiskEngine, TradeIntent

REPO = Path(__file__).resolve().parents[3]
SYM = "NIFTY 25000 CE"


def approve(cid, action="ENTRY", **kw):
    return RiskDecision(True, cid, action, "OK", "test", kw.get("ts", datetime.now(IST)))


def buy(**kw):
    return TradeIntent(symbol=SYM, side="BUY", lots=1, lot_size=65, instrument_id="43210", **kw)


def place(broker, intent):
    return broker.place_order(intent, approve(intent.client_order_id, broker.action_for(intent)))


@pytest.mark.parametrize("case", ["none", "vetoed", "other_order", "wrong_action", "stale"])
def test_refuses_without_matching_fresh_approval(case):
    broker, intent = PaperBroker(), buy()
    cid = intent.client_order_id
    decision = {
        "none": None,
        "vetoed": RiskDecision(False, cid, "ENTRY", "MAX_LOTS", "veto", datetime.now(IST)),
        "other_order": approve("someone-else"),
        "wrong_action": approve(cid, "EXIT"),
        "stale": approve(cid, ts=datetime.now(IST) - timedelta(minutes=5)),
    }[case]
    with pytest.raises(OrderRefused):
        broker.place_order(intent, decision)
    assert broker.orders == {}


@pytest.mark.parametrize("ticks,expected_buy,expected_sell", [(0, 100.0, 100.0), (1, 100.05, 99.95), (3, 100.15, 99.85)])
def test_market_fills_on_next_tick_with_configurable_slippage(ticks, expected_buy, expected_sell):
    broker = PaperBroker(slippage_ticks=ticks)
    order = place(broker, buy())
    assert order.state == OrderState.SUBMITTED and order.filled_qty == 0  # not filled at placement
    broker.on_tick(SYM, 100.0)
    assert order.state == OrderState.FILLED and order.avg_fill_price == expected_buy
    sell = place(broker, TradeIntent(symbol=SYM, side="SELL", lots=1, lot_size=65, purpose="EXIT",
                                     exit_reason="MANUAL"))
    broker.on_tick(SYM, 100.0)
    assert sell.avg_fill_price == expected_sell
    assert broker.get_positions() == []


def test_limit_waits_until_price_crosses():
    broker = PaperBroker()
    order = place(broker, buy(order_type="LIMIT", price=98.0))
    broker.on_tick(SYM, 99.0)
    assert order.state == OrderState.SUBMITTED
    broker.on_tick(SYM, 97.9)
    assert order.state == OrderState.FILLED and order.avg_fill_price == 97.95  # ltp + 1 tick, <= limit


def test_stop_market_triggers_then_fills():
    broker = PaperBroker()
    place(broker, buy())
    broker.on_tick(SYM, 100.0)
    stop = place(broker, TradeIntent(symbol=SYM, side="SELL", lots=1, lot_size=65, order_type="SL-M",
                                     trigger_price=95.0, purpose="EXIT", exit_reason="STOP_HIT"))
    broker.on_tick(SYM, 96.0)
    assert stop.state == OrderState.SUBMITTED
    broker.on_tick(SYM, 94.5)
    assert stop.state == OrderState.FILLED and stop.avg_fill_price == 94.45


def test_same_intent_twice_is_one_order():
    broker, intent = PaperBroker(), buy()
    assert place(broker, intent) is place(broker, intent)
    broker.on_tick(SYM, 100.0)
    assert broker.get_positions()[0].net_qty == 65


def test_super_order_target_leg_wins_and_stop_is_cancelled():
    led = Ledger(":memory:", rates=load_rates(REPO / "config" / "charges.yaml"))
    broker = PaperBroker()
    attach_ledger(broker, led)
    intent = buy(target=130.0, stop_loss=90.0, decision_price=100.0)
    entry = broker.place_super_order(intent, approve(intent.client_order_id))
    broker.on_tick(SYM, 100.0)  # entry fills @ 100.05, legs created
    tgt, stop = broker.orders[f"{intent.client_order_id}-T"], broker.orders[f"{intent.client_order_id}-S"]
    broker.on_tick(SYM, 131.0)
    assert entry.state == tgt.state == OrderState.FILLED
    assert stop.state == OrderState.CANCELLED and stop.cancel_reason == "OCO_SIBLING_FILLED"
    (trade,) = led.trades()
    assert trade["status"] == "CLOSED" and trade["exit_reason"] == "TARGET_HIT"
    assert trade["entry_slippage"] == 0.05 and trade["exit_slippage"] == 0.95  # 130.95 vs target 130
    assert trade["net_pnl"] == round(trade["gross_pnl"] - trade["charges"], 2)
    assert [e["to_state"] for e in led.order_events(stop.client_order_id)] == ["SUBMITTED", "CANCELLED"]


def test_super_order_trailing_stop_and_target_shift():
    broker = PaperBroker(slippage_ticks=0)
    intent = buy(target=150.0, stop_loss=90.0, trailing_jump=5.0)
    entry = broker.place_super_order(intent, approve(intent.client_order_id))
    broker.on_tick(SYM, 100.0)
    stop = broker.orders[f"{intent.client_order_id}-S"]
    tgt = broker.orders[f"{intent.client_order_id}-T"]
    broker.on_tick(SYM, 112.0)  # +12 from entry: two 5-pt steps
    assert stop.trigger_price == 100.0
    broker.modify_order(entry, approve(intent.client_order_id, "MODIFY"), target=160.0)
    assert tgt.price == 160.0
    broker.on_tick(SYM, 99.0)
    assert stop.state == OrderState.FILLED and stop.avg_fill_price == 99.0
    assert tgt.state == OrderState.CANCELLED


def test_cancel_and_modify_rules():
    broker = PaperBroker()
    order = place(broker, buy(order_type="LIMIT", price=90.0))
    broker.modify_order(order, approve(order.client_order_id, "MODIFY"), price=91.0)
    assert order.price == 91.0
    with pytest.raises(OrderRefused):
        broker.cancel_order(order, approve(order.client_order_id, "ENTRY"))
    broker.cancel_order(order, approve(order.client_order_id, "CANCEL"), reason="BOSS_CHANGED_MIND")
    assert order.state == OrderState.CANCELLED and order.cancel_reason == "BOSS_CHANGED_MIND"
    with pytest.raises(InvalidTransition):
        broker.modify_order(order, approve(order.client_order_id, "MODIFY"), price=92.0)


def test_flatten_all_cancels_orders_and_exits_positions():
    broker = PaperBroker()
    place(broker, buy())
    broker.on_tick(SYM, 100.0)
    pending = place(broker, buy(order_type="LIMIT", price=50.0))
    exits = broker.flatten_all(approve("FLATTEN_ALL", "FLATTEN"))
    assert pending.state == OrderState.CANCELLED and pending.cancel_reason == "KILL_SWITCH"
    assert len(exits) == 1 and exits[0].intent.exit_reason == "KILL_SWITCH"
    broker.on_tick(SYM, 101.0)
    assert broker.get_positions() == []


def test_risk_engine_to_paper_broker_to_ledger(tmp_path):
    cfg = yaml.safe_load((REPO / "config" / "risk_limits.yaml").read_text())
    cfg.update(entry_start_ist="00:00", entry_cutoff_ist="23:59:59", kill_switch_file=str(tmp_path / "KS"))
    (tmp_path / "risk.yaml").write_text(yaml.safe_dump(cfg))
    led = Ledger(tmp_path / "ledger.sqlite", rates=load_rates(REPO / "config" / "charges.yaml"))
    engine = RiskEngine(ledger=led, config_path=tmp_path / "risk.yaml")
    broker = PaperBroker()
    attach_ledger(broker, led)

    intent = buy(decision_price=100.0, stop_loss=95.0)
    order = broker.place_order(intent, engine.check_entry(intent))
    broker.on_tick(SYM, 100.0)
    assert order.state == OrderState.FILLED
    assert engine.check_entry(buy(decision_price=100.0, stop_loss=95.0)).reason_code == "DUPLICATE"
    assert led.open_positions()[0]["net_qty"] == 65
    vetoed = buy(decision_price=100.0, stop_loss=95.0, trade_id="other")
    with pytest.raises(OrderRefused):
        broker.place_order(vetoed, engine.check_entry(vetoed))


def test_spof_S10_ledger_hook_failure_leaves_no_orphan_order():
    from brokers import LedgerWriteFailed

    broker = PaperBroker()
    calls = []

    def hook(order, prev, to, reason):
        calls.append(to)
        if to == OrderState.SUBMITTED:
            raise OSError(28, "No space left on device")

    broker.on_transition = hook
    intent = buy(order_type="MARKET")
    with pytest.raises(LedgerWriteFailed):
        place(broker, intent)
    order = next(iter(broker.orders.values()), None)
    if order is not None:  # the broker kept the object: it must not claim SUBMITTED
        assert order.state != OrderState.SUBMITTED
        assert all(h["to"] != "SUBMITTED" for h in order.history)
    assert calls == [OrderState.SUBMITTED]
