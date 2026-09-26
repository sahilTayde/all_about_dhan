"""Reconciliation: every mismatch kind, alarm logged + recorded, entries halted until clean."""

import logging
from datetime import datetime
from pathlib import Path

import pytest

from brokers import (
    OrderSnapshot,
    OrderState,
    PaperBroker,
    Position,
    attach_ledger,
    compare_orders,
    compare_positions,
    reconcile,
)
from ledger import Ledger, load_rates
from risk_engine import IST, RiskDecision, RiskEngine, TradeIntent

REPO = Path(__file__).resolve().parents[3]


def test_position_mismatch_kinds():
    internal = [Position("A", 65, instrument_id="1"), Position("B", 65, instrument_id="2"), Position("C", 130, instrument_id="3")]
    broker = [Position("B", 65, instrument_id="2"), Position("C", 65, instrument_id="3"), Position("D", 65, instrument_id="4")]
    got = {(m.kind, m.key, m.internal, m.broker) for m in compare_positions(internal, broker)}
    assert got == {("ORPHAN_INTERNAL", "1", 65, None), ("QTY_MISMATCH", "3", 130, 65), ("ORPHAN_BROKER", "4", None, 65)}
    assert compare_positions(internal[1:2], broker[:1]) == []


def test_order_mismatch_kinds():
    internal = [
        {"client_order_id": "ok", "status": "SUBMITTED"},
        {"client_order_id": "lagging", "status": "SUBMITTED"},
        {"client_order_id": "lost", "status": "PARTIAL"},
        {"client_order_id": "never-sent", "status": "NEW"},
    ]
    broker = [
        OrderSnapshot("ok", "1", OrderState.SUBMITTED),
        OrderSnapshot("lagging", "2", OrderState.FILLED, 65),
        OrderSnapshot("", "3", OrderState.SUBMITTED),  # placed outside this system (Dhan app)
    ]
    got = {(m.kind, m.key) for m in compare_orders(internal, broker)}
    assert got == {("ORDER_STATE_MISMATCH", "lagging"), ("ORDER_MISSING_AT_BROKER", "lost"), ("ORPHAN_BROKER_ORDER", "3")}


def test_mismatch_raises_alarm_and_halts_entries_until_clean(tmp_path, caplog):
    led = Ledger(":memory:", rates=load_rates(REPO / "config" / "charges.yaml"))
    broker = PaperBroker()
    attach_ledger(broker, led)
    it = TradeIntent(symbol="NIFTY 25000 CE", side="BUY", lots=1, lot_size=65, instrument_id="43210")
    broker.place_order(it, RiskDecision(True, it.client_order_id, "ENTRY", "OK", "", datetime.now(IST)))
    broker.on_tick(it.symbol, 100.0)
    assert reconcile(broker, led) == []

    broker._positions.clear()  # position vanished at the "broker" (e.g. squared off in the Dhan app)
    with caplog.at_level(logging.ERROR, logger="brokers.reconcile"):
        (m,) = reconcile(broker, led)
    assert (m.kind, m.key, m.internal) == ("ORPHAN_INTERNAL", "43210", 65)
    assert "RECONCILIATION MISMATCH ALARM" in caplog.text
    assert led.risk_snapshot(datetime.now(IST), 60)["recon_ok"] is False

    cfg = tmp_path / "risk.yaml"
    cfg.write_text((REPO / "config" / "risk_limits.yaml").read_text())
    engine = RiskEngine(ledger=led, config_path=cfg)
    probe = TradeIntent(symbol="BANKNIFTY", side="BUY", lots=1, lot_size=30, decision_price=100.0, stop_loss=90.0)
    ten_am = datetime.fromisoformat("2026-09-28T10:00:00+05:30")
    assert engine.check_entry(probe, ten_am).reason_code == "RECON_MISMATCH"

    broker._positions["NIFTY 25000 CE"] = Position("NIFTY 25000 CE", 65, 100.05, "43210")
    assert reconcile(broker, led) == []
    assert engine.check_entry(probe, ten_am).approved


def test_broker_error_counts_as_mismatch():
    class DownBroker(PaperBroker):
        def get_positions(self):
            raise ConnectionError("dhan unreachable")

    led = Ledger(":memory:", rates=load_rates(REPO / "config" / "charges.yaml"))
    (m,) = reconcile(DownBroker(), led)
    assert m.kind == "RECON_ERROR" and "unreachable" in m.broker
    assert led.risk_snapshot(datetime.now(IST), 60)["recon_ok"] is False


@pytest.mark.parametrize("net_qty,kind", [(65, None), (130, "QTY_MISMATCH")])
def test_reconcile_against_mocked_dhan_positions(tmp_path, net_qty, kind):
    from test_dhan_broker import make  # same mocked HTTP layer; read-only calls, any mode

    broker = make(tmp_path, "paper")
    broker.fake.responses[("GET", "/v2/positions")] = (200, [{"tradingSymbol": "N", "securityId": "43210", "netQty": net_qty, "buyAvg": 100.0}])
    broker.fake.responses[("GET", "/v2/orders")] = (200, [])
    led = Ledger(":memory:", rates=load_rates(REPO / "config" / "charges.yaml"))
    led.record_order({"client_order_id": "E1", "broker": "dhan", "mode": "limited_live", "symbol": "N",
                      "instrument_id": "43210", "side": "BUY", "qty": 65, "order_type": "MARKET",
                      "purpose": "ENTRY", "filled_qty": 0}, "NEW", "SUBMITTED")
    led.record_fill("E1", 65, 100.0)
    led.record_order({"client_order_id": "E1", "broker": "dhan", "mode": "limited_live", "symbol": "N",
                      "instrument_id": "43210", "side": "BUY", "qty": 65, "order_type": "MARKET",
                      "purpose": "ENTRY", "filled_qty": 65}, "SUBMITTED", "FILLED")
    got = [m.kind for m in reconcile(broker, led)]
    assert got == ([] if kind is None else [kind])
