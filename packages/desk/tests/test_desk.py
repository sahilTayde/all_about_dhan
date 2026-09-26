"""Desk: founder first, risk veto = no trade, PaperBroker + ledger mirror, stops without the boss."""

from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

from brokers import OrderRefused, attach_ledger
from desk import BROKER_REFUSED, FOUNDER_PAUSED, RISK_VETO, ClockedPaperBroker, Desk, client_order_id
from desk.executor import ist
from desk_ml import paper_scalp as ps
from desk_ml.features import Triple
from events import EventAuditLog, MemoryBus
from ledger import Ledger
from risk_engine import IST, RiskDecision, RiskEngine, TradeIntent

REPO = Path(__file__).resolve().parents[3]
REPLAY_RISK = REPO / "config" / "risk_limits_replay.yaml"
T0 = int(datetime(2026, 9, 10, 10, 30, tzinfo=IST).timestamp())


def make_desk(tmp_path, risk_config=REPLAY_RISK):
    engine = ps.BookEngine(root=tmp_path)
    engine.lot_by_und["NIFTY"] = (65, "test")
    audit = EventAuditLog()
    bus = MemoryBus(audit)
    led = Ledger(":memory:", charges_path=REPO / "config" / "charges.yaml")
    risk = RiskEngine(led, config_path=risk_config)
    holder = {}
    broker = ClockedPaperBroker(clock=lambda: holder["desk"].clock(), slippage_ticks=0)
    attach_ledger(broker, led)
    steps = {}
    desk = Desk(bus, engine, risk=risk, broker=broker, steps=steps)
    holder["desk"] = desk
    desk.now, desk.now_ts = ist(T0), T0
    return desk, bus, audit, led, steps


def ticket(ts=T0, *, filled=True, side="CE", **kw):
    fields = dict(
        book_id=ps.SOD_PRODUCT_BOOK, underlying="NIFTY", side=side, trade_id=f"paper-test-NIFTY-{ts}-{side}",
        entry=150.0, stop=140.0, target=170.0, atm_strike=24800.0, opened_ts=ts, opened_bar=1,
        strike_source="ITM_100", limit_price=150.0, lot_size=65, lots=20, qty=1300, filled=filled,
        last_ltp=150.0, index_regime="TREND", agent_status="IN_TRADE" if filled else "WORKING_LIMIT",
    )
    return ps.OpenPaper(**{**fields, **kw})


def approve(bus, pos):
    bus.publish("ENTRY_APPROVED", {"trade_id": pos.trade_id, "ticket": asdict(pos)}, source="boss")


def restrictive_config(tmp_path, **paper):
    cfg = yaml.safe_load(REPLAY_RISK.read_text())
    cfg["modes"]["paper"].update(paper)
    path = tmp_path / "risk.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


def test_approved_entry_goes_risk_then_broker_then_ledger(tmp_path):
    desk, bus, audit, led, _ = make_desk(tmp_path)
    pos = ticket()
    approve(bus, pos)
    assert (pos.book_id, "NIFTY") in desk.engine.opens and not bus.errors
    order = desk.broker.orders[client_order_id(pos.trade_id, "E")]
    assert order.state.value == "FILLED" and order.avg_fill_price == 150.0 and order.intent.qty == 1300
    decisions = led.conn.execute("SELECT action, approved FROM risk_decisions").fetchall()
    assert [tuple(r) for r in decisions] == [("ENTRY", 1)]
    assert [t["status"] for t in led.trades()] == ["OPEN"]
    assert audit.counts() == {"ENTRY_APPROVED": 1, "ORDER_FILLED": 1, "ORDER_SUBMITTED": 1}


def test_risk_veto_means_no_trade(tmp_path):
    desk, bus, audit, led, _ = make_desk(tmp_path, restrictive_config(tmp_path, max_lots_per_trade=5))
    approve(bus, ticket())
    assert desk.engine.opens == {} and desk.broker.orders == {} and led.trades() == []
    assert desk.engine.skips[-1]["reason"] == RISK_VETO and desk.engine.skips[-1]["reason_code"] == "MAX_LOTS"
    assert audit.counts()["ENTRY_VETOED"] == 1


def test_risk_engine_error_means_no_trade(tmp_path):
    desk, bus, _audit, _led, _ = make_desk(tmp_path, tmp_path / "missing.yaml")
    approve(bus, ticket())
    assert desk.engine.opens == {} and desk.broker.orders == {}
    assert desk.vetoes[-1]["reason_code"] == "ENGINE_ERROR"


def test_unsizable_ticket_means_no_trade(tmp_path):
    desk, bus, _audit, _led, _ = make_desk(tmp_path)
    approve(bus, ticket(lot_size=None))
    assert desk.engine.opens == {} and desk.vetoes[-1]["reason_code"] == "ENGINE_ERROR"


def test_live_mode_without_founder_confirm_is_vetoed(tmp_path, monkeypatch):
    monkeypatch.delenv("ALL_ABOUT_DHAN_LIVE_CONFIRM", raising=False)
    cfg = yaml.safe_load(REPLAY_RISK.read_text())
    cfg["mode"] = "live"
    path = tmp_path / "live.yaml"
    path.write_text(yaml.safe_dump(cfg))
    desk, bus, _audit, _led, _ = make_desk(tmp_path, path)
    approve(bus, ticket())
    assert desk.engine.opens == {} and desk.vetoes[-1]["reason_code"] == "MODE_NOT_ENABLED"


def test_founder_pause_resume_and_flatten(tmp_path):
    desk, bus, audit, led, _ = make_desk(tmp_path)
    bus.publish("FOUNDER_COMMAND", {"command": "PAUSE_ENTRIES"}, source="founder")
    approve(bus, ticket())
    assert desk.engine.opens == {} and desk.engine.skips[-1]["reason"] == FOUNDER_PAUSED
    bus.publish("FOUNDER_COMMAND", {"command": "RESUME_ENTRIES"}, source="founder")
    pos = ticket(T0 + 10)
    approve(bus, pos)
    working = ticket(T0 + 10, filled=False, side="PE", book_id="MIX-ML-LOGIT")
    approve(bus, working)
    assert len(desk.engine.opens) == 2
    desk.engine.opens[(pos.book_id, "NIFTY")].last_ltp = 158.0
    bus.publish("FOUNDER_COMMAND", {"command": "FLATTEN_ALL"}, source="founder")
    assert desk.engine.opens == {} and desk.paused
    rows = {r["trade_id"]: r for r in desk.engine.closed}
    assert rows[pos.trade_id]["exit_reason"] == "FOUNDER_COMMAND" and rows[pos.trade_id]["exit"] == 158.0
    assert rows[working.trade_id]["filled"] is False
    trades = {t["trade_id"]: t for t in led.trades()}
    assert trades[pos.trade_id]["status"] == "CLOSED" and trades[pos.trade_id]["exit_reason"] == "FOUNDER_COMMAND"
    assert trades[pos.trade_id]["gross_pnl"] == pytest.approx(8.0 * 1300)
    assert led.open_positions() == []
    assert audit.counts()["ORDER_CANCELLED"] == 1
    approve(bus, ticket(T0 + 20))
    assert desk.engine.opens == {}


def test_stop_exits_on_tick_without_the_boss(tmp_path):
    desk, bus, _audit, led, steps = make_desk(tmp_path)
    pos = ticket()
    approve(bus, pos)
    prev = Triple(ts=T0, idx_close=25000.0, ce_close=60.0, pe_close=60.0, atm_strike=25000.0,
                  itm_ce_close=150.0, itm_pe_close=40.0, itm_ce_strike=24800.0, itm_pe_strike=25200.0,
                  premium_kind="ITM")
    tick = Triple(ts=T0 + 20, idx_close=24980.0, ce_close=50.0, pe_close=70.0, atm_strike=25000.0,
                  itm_ce_close=130.0, itm_pe_close=45.0, itm_ce_strike=24800.0, itm_pe_strike=25200.0,
                  premium_kind="ITM")
    steps["NIFTY:2"] = ps.TickStep(und="NIFTY", i=2, tick=tick, prev=prev, classified={}, bin_rec={}, dealer={},
                                   strike=25000.0)
    bus.publish("MARKET_TICK", {"key": "NIFTY:2"}, source="feed")  # no boss subscribed at all
    assert not bus.errors and desk.engine.opens == {}
    row = desk.engine.closed[-1]
    assert row["exit_reason"] == "STOP" and row["filled"] and row["exit"] <= pos.stop
    (trade,) = led.trades()
    assert trade["status"] == "CLOSED" and trade["exit_reason"] == "STOP_HIT"
    assert trade["exit_time"] == ist(T0 + 20).isoformat(timespec="seconds")


def test_unfilled_working_limit_cancel_is_mirrored(tmp_path):
    desk, bus, _audit, led, _ = make_desk(tmp_path)
    pos = ticket(filled=False)
    approve(bus, pos)
    order = desk.broker.orders[client_order_id(pos.trade_id, "E")]
    assert order.state.value == "SUBMITTED"
    desk.close(pos, ltp=152.0, ts=T0 + 60, reason="CANCEL_UNFILLED_FLAT")
    assert order.state.value == "CANCELLED" and order.cancel_reason == "EOD"
    assert [t["status"] for t in led.trades()] == ["CANCELLED"]


def test_broker_still_requires_matching_fresh_approval():
    now = datetime(2026, 9, 10, 10, 30, tzinfo=IST)
    broker = ClockedPaperBroker(clock=lambda: now)
    intent = TradeIntent(symbol="NIFTY 24800 CE", side="BUY", lots=1, lot_size=65, decision_price=100.0, stop_loss=90.0)
    ok = RiskDecision(True, intent.client_order_id, "ENTRY", "OK", "t", now)
    for bad in (None,
                RiskDecision(False, intent.client_order_id, "ENTRY", "MAX_LOTS", "t", now),
                RiskDecision(True, "someone-else", "ENTRY", "OK", "t", now),
                RiskDecision(True, intent.client_order_id, "EXIT", "OK", "t", now),
                RiskDecision(True, intent.client_order_id, "ENTRY", "OK", "t", now - timedelta(minutes=5))):
        with pytest.raises(OrderRefused):
            broker.place_order(intent, bad)
    assert broker.place_order(intent, ok).state.value == "SUBMITTED"


def test_broker_refusal_means_no_trade(tmp_path, monkeypatch):
    desk, bus, _audit, _led, _ = make_desk(tmp_path)
    monkeypatch.setattr(desk.broker, "max_decision_age_s", -10.0)
    approve(bus, ticket())
    assert desk.engine.opens == {} and desk.engine.skips[-1]["reason"] == BROKER_REFUSED
