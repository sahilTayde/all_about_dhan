"""Desk: founder first, risk veto = no trade, PaperBroker + ledger mirror, stops without the boss."""

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

from brokers import OrderRefused, attach_ledger
from desk import BROKER_REFUSED, FAILSAFE_MTM, FOUNDER_PAUSED, MTM_HALT, RISK_VETO, ClockedPaperBroker, Desk, client_order_id
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
    desk = Desk(bus, engine, risk=risk, broker=broker, steps=steps, health_alerts_path=tmp_path / "alerts.jsonl")
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


def _tick(ts):
    prev = Triple(ts=ts - 20, idx_close=25000.0, ce_close=60.0, pe_close=60.0, atm_strike=25000.0,
                  itm_ce_close=150.0, itm_pe_close=40.0, itm_ce_strike=24800.0, itm_pe_strike=25200.0,
                  premium_kind="ITM")
    tick = Triple(ts=ts, idx_close=24980.0, ce_close=50.0, pe_close=70.0, atm_strike=25000.0,
                  itm_ce_close=130.0, itm_pe_close=45.0, itm_ce_strike=24800.0, itm_pe_strike=25200.0,
                  premium_kind="ITM")
    return ps.TickStep(und="NIFTY", i=2, tick=tick, prev=prev, classified={}, bin_rec={}, dealer={}, strike=25000.0)


def test_mtm_error_closes_on_the_same_tick_and_blocks_entries(tmp_path, monkeypatch):
    """A mark/stop error closes the ticket at the last good quote on that tick and blocks new entries."""
    desk, bus, audit, _led, steps = make_desk(tmp_path)
    pos = ticket()
    pos.last_ltp = 142.0
    approve(bus, pos)
    assert (pos.book_id, "NIFTY") in desk.engine.opens

    def boom(_engine, _s):
        raise RuntimeError("bad mark")

    monkeypatch.setattr(desk._ps, "step_mark", boom)
    steps["NIFTY:2"] = _tick(T0 + 20)
    bus.publish("MARKET_TICK", {"key": "NIFTY:2"}, source="feed")
    assert desk.entries_blocked and not bus.errors
    assert desk.engine.opens == {}
    row = desk.engine.closed[-1]
    assert row["exit_reason"] == FAILSAFE_MTM and row["exit"] == pytest.approx(142.0)
    assert row["closed_ts"] == T0 + 20
    closed = audit.rows("POSITION_CLOSED")
    assert closed[-1]["payload"]["exit_reason"] == FAILSAFE_MTM
    alerts = audit.rows("HEALTH_ALERT")
    assert alerts and alerts[-1]["payload"]["check"] == "desk_mtm"
    assert "bad mark" in alerts[-1]["payload"]["reason"] and alerts[-1]["payload"]["entries_blocked"] is True

    steps["NIFTY:3"] = _tick(T0 + 40)
    bus.publish("MARKET_TICK", {"key": "NIFTY:3"}, source="feed")
    alert_lines = (tmp_path / "alerts.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(alert_lines) == 1 and len(audit.rows("HEALTH_ALERT")) == 1

    def other(_engine, _s):
        raise ValueError("bad quote")

    monkeypatch.setattr(desk._ps, "step_mark", other)
    steps["NIFTY:4"] = _tick(T0 + 50)
    bus.publish("MARKET_TICK", {"key": "NIFTY:4"}, source="feed")
    kinds = [json.loads(line)["error_kind"] for line in (tmp_path / "alerts.jsonl").read_text(encoding="utf-8").splitlines()]
    assert kinds == ["RuntimeError", "ValueError"]

    later = ticket(T0 + 60, side="PE")
    approve(bus, later)
    assert later.trade_id not in {p.trade_id for p in desk.engine.opens.values()}
    assert desk.engine.skips[-1]["reason"] == MTM_HALT
    bus.publish("FOUNDER_COMMAND", {"command": "RESUME_ENTRIES"}, source="founder")
    assert desk.entries_blocked and not desk.paused

    from api import health_alerts
    from fastapi.testclient import TestClient
    from api.main import create_app

    monkeypatch.setattr(health_alerts, "HEALTH_DIR", tmp_path)
    body = TestClient(create_app()).get("/health/alerts").json()
    assert body["count"] == 2
    assert [a["error_kind"] for a in body["alerts"]] == ["ValueError", "RuntimeError"]
    top = body["alerts"][0]
    assert top["event"] == "ALERT" and top["check"] == "desk_mtm" and top["severity"] == "CRITICAL"
    assert "bad quote" in top["message"]
    assert "bad mark" in body["alerts"][1]["message"]


def test_mtm_block_persists_across_a_new_desk(tmp_path, monkeypatch):
    """The live loop rebuilds the desk every cycle. The block and the one alert stay."""
    desk, bus, _audit, _led, steps = make_desk(tmp_path)
    pos = ticket()
    approve(bus, pos)
    real_mark = ps.step_mark
    monkeypatch.setattr(ps, "step_mark", lambda _e, _s: (_ for _ in ()).throw(RuntimeError("bad mark")))
    steps["NIFTY:2"] = _tick(T0 + 20)
    bus.publish("MARKET_TICK", {"key": "NIFTY:2"}, source="feed")
    assert (tmp_path / "data" / "desk" / "mtm_halt.json").is_file()
    monkeypatch.setattr(ps, "step_mark", real_mark)

    desk2, bus2, _audit2, _led2, steps2 = make_desk(tmp_path)
    assert desk2.entries_blocked is False
    steps2["NIFTY:2"] = _tick(T0 + 40)
    bus2.publish("MARKET_TICK", {"key": "NIFTY:2"}, source="feed")
    assert desk2.entries_blocked
    approve(bus2, ticket(T0 + 80, side="PE"))
    assert desk2.engine.skips[-1]["reason"] == MTM_HALT
    assert len((tmp_path / "alerts.jsonl").read_text(encoding="utf-8").splitlines()) == 1

    stale = json.loads((tmp_path / "data" / "desk" / "mtm_halt.json").read_text())
    stale["session"] = "2026-09-09"
    (tmp_path / "data" / "desk" / "mtm_halt.json").write_text(json.dumps(stale), encoding="utf-8")
    desk3, bus3, _a3, _l3, steps3 = make_desk(tmp_path)
    steps3["NIFTY:2"] = _tick(T0 + 100)
    bus3.publish("MARKET_TICK", {"key": "NIFTY:2"}, source="feed")
    assert desk3.entries_blocked is False


def test_strict_risk_veto_logs_ticket_risk(tmp_path):
    """config/risk_limits.yaml is unchanged. A veto still shows the reason and the rupee risk."""
    desk, bus, audit, led, _steps = make_desk(tmp_path, REPO / "config" / "risk_limits.yaml")
    approve(bus, ticket())  # (150-140) x 1300 = ₹13,000 against the ₹5,000 cap
    assert desk.engine.opens == {}
    veto = audit.rows("ENTRY_VETOED")[-1]["payload"]
    assert veto["reason_code"] == "MAX_LOSS_PER_TRADE"
    assert veto["ticket_risk_inr"] == pytest.approx(13000)
    assert "13,000" in veto["reason"] or "13000" in veto["reason"]
    stored = led.conn.execute(
        "SELECT reason_code, intent_json FROM risk_decisions WHERE approved = 0"
    ).fetchone()
    assert stored[0] == "MAX_LOSS_PER_TRADE"
    assert json.loads(stored[1])["ticket_risk_inr"] == pytest.approx(13000)


def test_failsafe_price_uses_the_tick_when_the_last_quote_is_missing():
    from types import SimpleNamespace

    from desk.executor import Desk

    bare = object.__new__(Desk)
    step = _tick(T0)
    pos = SimpleNamespace(last_ltp=None, side="CE", entry=150.0)
    assert bare._failsafe_price(pos, step) == pytest.approx(130.0)  # this tick's ITM CE
    pos.side = "PE"
    assert bare._failsafe_price(pos, step) == pytest.approx(45.0)
    assert bare._failsafe_price(SimpleNamespace(last_ltp=None, side="CE", entry=150.0), None) == pytest.approx(150.0)


def test_broker_refusal_means_no_trade(tmp_path, monkeypatch):
    desk, bus, _audit, _led, _ = make_desk(tmp_path)
    monkeypatch.setattr(desk.broker, "max_decision_age_s", -10.0)
    approve(bus, ticket())
    assert desk.engine.opens == {} and desk.engine.skips[-1]["reason"] == BROKER_REFUSED
