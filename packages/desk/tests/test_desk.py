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


def make_desk(tmp_path, risk_config=REPLAY_RISK, *, live_loop=False):
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
    desk = Desk(
        bus, engine, risk=risk, broker=broker, steps=steps,
        health_alerts_path=tmp_path / "alerts.jsonl", live_loop=live_loop,
    )
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


def _halt_file(tmp_path):
    return tmp_path / "data" / "desk" / "live_loop" / "mtm_halt.json"


def test_halt_keeps_earlier_trades_on_the_next_cycle(tmp_path, monkeypatch):
    """Two live-loop cycles. Trades before the halt stay. Entries at or after it do not."""
    def mark(_engine, step):
        if int(step.tick.ts) >= T0 + 200:
            raise RuntimeError("bad mark")

    monkeypatch.setattr(ps, "step_mark", mark)
    desk, bus, _audit, _led, steps = make_desk(tmp_path, live_loop=True)
    early = ticket(T0 + 30)
    approve(bus, early)
    assert (early.book_id, "NIFTY") in desk.engine.opens
    steps["NIFTY:2"] = _tick(T0 + 200)
    bus.publish("MARKET_TICK", {"key": "NIFTY:2"}, source="feed")
    assert desk.engine.opens == {}
    assert desk.halt_from_ts == T0 + 200
    saved = json.loads(_halt_file(tmp_path).read_text(encoding="utf-8"))
    assert saved["halt_ts"] == T0 + 200 and saved["session"] == "2026-09-10"
    assert "RuntimeError" in saved["kinds"]
    late = ticket(T0 + 400, side="PE")
    approve(bus, late)
    assert desk.engine.skips[-1]["reason"] == MTM_HALT

    early_bird, early_bus, _ae, _le, _se = make_desk(tmp_path, live_loop=True)
    first = ticket(T0 + 400, side="PE")
    approve(early_bus, first)  # an entry before this desk's first tick still sees the saved halt
    assert early_bird.engine.opens == {} and early_bird.engine.skips[-1]["reason"] == MTM_HALT

    desk2, bus2, _a2, _l2, steps2 = make_desk(tmp_path, live_loop=True)
    steps2["NIFTY:1"] = _tick(T0 + 40)
    bus2.publish("MARKET_TICK", {"key": "NIFTY:1"}, source="feed")
    again = ticket(T0 + 40)
    approve(bus2, again)
    assert (again.book_id, "NIFTY") in desk2.engine.opens
    blocked = ticket(T0 + 400, side="PE")
    approve(bus2, blocked)
    assert blocked.trade_id not in {p.trade_id for p in desk2.engine.opens.values()}
    assert desk2.engine.skips[-1]["reason"] == MTM_HALT
    assert len((tmp_path / "alerts.jsonl").read_text(encoding="utf-8").splitlines()) == 1

    lab, lab_bus, _al, _ll, lab_steps = make_desk(tmp_path, live_loop=False)
    lab_steps["NIFTY:1"] = _tick(T0 + 40)
    lab_bus.publish("MARKET_TICK", {"key": "NIFTY:1"}, source="feed")
    lab_ticket = ticket(T0 + 500, side="CE")
    approve(lab_bus, lab_ticket)
    assert (lab_ticket.book_id, "NIFTY") in lab.engine.opens

    saved["session"] = "2026-09-09"
    _halt_file(tmp_path).write_text(json.dumps(saved), encoding="utf-8")
    nxt, nxt_bus, _an, _ln, nxt_steps = make_desk(tmp_path, live_loop=True)
    nxt_steps["NIFTY:1"] = _tick(T0 + 40)
    nxt_bus.publish("MARKET_TICK", {"key": "NIFTY:1"}, source="feed")
    tomorrow = ticket(T0 + 500, side="PE")
    approve(nxt_bus, tomorrow)
    assert (tomorrow.book_id, "NIFTY") in nxt.engine.opens


def test_corrupt_halt_file_blocks_entries(tmp_path, caplog, monkeypatch):
    monkeypatch.setattr(ps, "step_mark", lambda _e, _s: None)
    path = _halt_file(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    desk, bus, audit, _led, steps = make_desk(tmp_path, live_loop=True)
    steps["NIFTY:1"] = _tick(T0 + 10)
    with caplog.at_level("ERROR", logger="desk"):
        bus.publish("MARKET_TICK", {"key": "NIFTY:1"}, source="feed")
    assert desk.halt_fail_closed and desk.entries_blocked
    assert "corrupt" in caplog.text
    approve(bus, ticket(T0 + 20))
    assert desk.engine.opens == {} and desk.engine.skips[-1]["reason"] == MTM_HALT
    alerts = audit.rows("HEALTH_ALERT")
    assert alerts and alerts[-1]["payload"]["error_kind"] == "halt_file"
    bus.publish("MARKET_TICK", {"key": "NIFTY:1"}, source="feed")
    assert len(audit.rows("HEALTH_ALERT")) == 1

    replay, replay_bus, _ar, _lr, replay_steps = make_desk(tmp_path, live_loop=False)
    replay_steps["NIFTY:1"] = _tick(T0 + 10)
    replay_bus.publish("MARKET_TICK", {"key": "NIFTY:1"}, source="feed")
    kept = ticket(T0 + 30)
    approve(replay_bus, kept)
    assert (kept.book_id, "NIFTY") in replay.engine.opens


def _alert_kinds(tmp_path):
    path = tmp_path / "alerts.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line)["error_kind"] for line in path.read_text(encoding="utf-8").splitlines()]


def _live_cycle(tmp_path, entry_ts=T0 + 30):
    """One live-loop cycle: a fresh desk, one tick, one entry attempt. Returns (desk, audit, pos)."""
    desk, bus, audit, _led, steps = make_desk(tmp_path, live_loop=True)
    steps["NIFTY:1"] = _tick(T0 + 10)
    bus.publish("MARKET_TICK", {"key": "NIFTY:1"}, source="feed")
    pos = ticket(entry_ts)
    approve(bus, pos)
    return desk, audit, pos


def test_corrupt_halt_alerts_once_across_live_loop_cycles(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "step_mark", lambda _e, _s: None)
    path = _halt_file(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    for _cycle in range(3):
        desk, _audit, pos = _live_cycle(tmp_path)
        assert desk.halt_fail_closed and desk.engine.opens == {}
        assert desk.engine.skips[-1]["reason"] == MTM_HALT
    assert _alert_kinds(tmp_path) == ["halt_file"]

    path.write_text("[1, 2]", encoding="utf-8")  # the file changed: say so once
    for _cycle in range(3):
        desk, _audit, _pos = _live_cycle(tmp_path)
        assert desk.halt_fail_closed and desk.engine.opens == {}
    assert _alert_kinds(tmp_path) == ["halt_file", "halt_file"]


@pytest.mark.parametrize(
    "shape", ["directory", "parent_is_file", "broken_symlink", "unreadable", "bad_utf8", "no_session", "bad_forced_close"],
)
def test_unreadable_halt_path_fails_closed(tmp_path, monkeypatch, shape):
    import os

    if shape == "unreadable" and os.geteuid() == 0:
        pytest.skip("root can read a chmod 000 file")
    monkeypatch.setattr(ps, "step_mark", lambda _e, _s: None)
    path = _halt_file(tmp_path)
    if shape == "parent_is_file":
        path.parent.parent.mkdir(parents=True)
        path.parent.write_text("not a folder", encoding="utf-8")
    else:
        path.parent.mkdir(parents=True)
    if shape == "directory":
        path.mkdir()
    elif shape == "broken_symlink":
        path.symlink_to(tmp_path / "gone.json")
    elif shape == "unreadable":
        path.write_text(json.dumps({"session": "2026-09-10", "halt_ts": T0 + 500}), encoding="utf-8")
        path.chmod(0)
    elif shape == "bad_utf8":
        path.write_bytes(b"\xff\xfe{}")
    elif shape == "no_session":
        path.write_text(json.dumps({"halt_ts": T0}), encoding="utf-8")
    elif shape == "bad_forced_close":
        path.write_text(json.dumps({"session": "2026-09-10", "halt_ts": T0 + 500,
                                    "forced_closes": [{"trade_id": "x"}]}), encoding="utf-8")
    for _cycle in range(3):
        desk, audit, _pos = _live_cycle(tmp_path)
        assert desk.halt_fail_closed and desk.engine.opens == {}
    assert _alert_kinds(tmp_path) == ["halt_file"]


def test_a_later_mtm_error_does_not_lift_a_corrupt_halt(tmp_path, monkeypatch):
    def mark(_engine, step):
        if int(step.tick.ts) >= T0 + 200:
            raise RuntimeError("bad mark")

    monkeypatch.setattr(ps, "step_mark", mark)
    path = _halt_file(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{half written", encoding="utf-8")
    desk, bus, _audit, _led, steps = make_desk(tmp_path, live_loop=True)
    steps["NIFTY:2"] = _tick(T0 + 200)
    bus.publish("MARKET_TICK", {"key": "NIFTY:2"}, source="feed")
    assert path.read_text(encoding="utf-8") == "{half written"
    for _cycle in range(2):
        again, _a, _p = _live_cycle(tmp_path)
        assert again.halt_fail_closed and again.engine.opens == {}
    assert path.read_text(encoding="utf-8") == "{half written"
    assert _alert_kinds(tmp_path) == ["halt_file", "RuntimeError"]


def _cycle_with_mark(tmp_path, monkeypatch, *, error_at=None):
    """A live-loop cycle over the same tape: entry at T0+30, ticks at T0+200 and T0+300.

    T0+300 is a target in the tape. ``error_at`` makes the mark fail on that tick (cycle 1 only).
    """
    def mark(engine, step):
        ts = int(step.tick.ts)
        if error_at is not None and ts >= error_at:
            raise RuntimeError("half-written tape line")
        for pos in list(engine.opens.values()):
            if ts >= T0 + 300:
                ps._close(engine, pos, ltp=170.0, ts=ts, reason="TARGET", root=engine.root)
            else:
                pos.last_ltp = 146.0

    monkeypatch.setattr(ps, "step_mark", mark)
    desk, bus, audit, _led, steps = make_desk(tmp_path, live_loop=True)
    steps["NIFTY:1"] = _tick(T0 + 10)
    bus.publish("MARKET_TICK", {"key": "NIFTY:1"}, source="feed")
    pos = ticket(T0 + 30)
    approve(bus, pos)
    for key, ts in (("NIFTY:2", T0 + 100), ("NIFTY:3", T0 + 200), ("NIFTY:4", T0 + 300)):
        steps[key] = _tick(ts)
        bus.publish("MARKET_TICK", {"key": key}, source="feed")
    return desk, audit, pos


def test_forced_close_is_replayed_when_the_error_goes_away(tmp_path, monkeypatch):
    """Cycle 1 errors at T0+200 and force-closes. Cycles 2 and 3 have a clean tape that would hit the
    target at T0+300. The booked result must stay the fail-safe close."""
    first, _a1, pos = _cycle_with_mark(tmp_path, monkeypatch, error_at=T0 + 200)
    (row1,) = [r for r in first.engine.closed if r["trade_id"] == pos.trade_id]
    assert row1["exit_reason"] == FAILSAFE_MTM and row1["exit"] == pytest.approx(146.0)
    saved = json.loads(_halt_file(tmp_path).read_text(encoding="utf-8"))
    assert saved["forced_closes"][0]["trade_id"] == pos.trade_id
    assert saved["forced_closes"][0]["closed_ts"] == T0 + 200 and saved["forced_closes"][0]["exit"] == 146.0
    assert saved["forced_closes"][0]["opened_ts"] == T0 + 30

    for _cycle in (2, 3):
        desk, audit, _p = _cycle_with_mark(tmp_path, monkeypatch, error_at=None)
        (row,) = [r for r in desk.engine.closed if r["trade_id"] == pos.trade_id]
        assert row["exit_reason"] == FAILSAFE_MTM and row["closed_ts"] == T0 + 200
        assert row["exit"] == row1["exit"] and row["realized_pnl_inr"] == row1["realized_pnl_inr"]
        assert [r["payload"]["exit_reason"] for r in audit.rows("POSITION_CLOSED")] == [FAILSAFE_MTM]
    assert _alert_kinds(tmp_path) == ["RuntimeError"]

    replay_desk, replay_bus, _ar, _lr, replay_steps = make_desk(tmp_path, live_loop=False)
    replay_steps["NIFTY:1"] = _tick(T0 + 10)
    replay_bus.publish("MARKET_TICK", {"key": "NIFTY:1"}, source="feed")
    approve(replay_bus, ticket(T0 + 30))
    replay_steps["NIFTY:4"] = _tick(T0 + 300)
    replay_bus.publish("MARKET_TICK", {"key": "NIFTY:4"}, source="feed")
    assert replay_desk.engine.closed[-1]["exit_reason"] == "TARGET"  # replays ignore the live-loop file


def test_unsaved_halt_is_kept_for_later_cycles_in_the_process(tmp_path, monkeypatch):
    from desk.executor import Desk

    def refuse(self, state):
        raise PermissionError(13, "read-only disk")

    monkeypatch.setattr(Desk, "_write_halt", refuse)
    first, _a1, pos = _cycle_with_mark(tmp_path, monkeypatch, error_at=T0 + 200)
    assert not _halt_file(tmp_path).exists()
    exit1 = first.engine.closed[-1]["exit"]
    for _cycle in (2, 3):
        desk, _audit, _p = _cycle_with_mark(tmp_path, monkeypatch, error_at=None)
        (row,) = [r for r in desk.engine.closed if r["trade_id"] == pos.trade_id]
        assert row["exit_reason"] == FAILSAFE_MTM and row["exit"] == exit1
        late = ticket(T0 + 400, side="PE")
        assert desk._entry_halted(int(late.opened_ts))
    assert sorted(_alert_kinds(tmp_path)) == ["RuntimeError", "halt_write"]


def test_strict_risk_file_books_a_typical_ticket_and_logs_a_veto(tmp_path):
    """Paper cap is ₹30,000. A ₹13,000 ticket books. A ₹31,037.50 ticket is vetoed with the reason split out."""
    desk, bus, audit, led, _steps = make_desk(tmp_path, REPO / "config" / "risk_limits.yaml")
    ok = ticket()  # (150-140) x 1300 = ₹13,000
    approve(bus, ok)
    assert (ok.book_id, "NIFTY") in desk.engine.opens
    big = ticket(T0 + 5, side="PE", book_id="MIX-ML-LOGIT", stop=130.9, lots=25, qty=1625)
    approve(bus, big)
    assert big.trade_id not in {p.trade_id for p in desk.engine.opens.values()}
    veto = audit.rows("ENTRY_VETOED")[-1]["payload"]
    assert veto["reason"] == RISK_VETO and veto["reason_code"] == "MAX_LOSS_PER_TRADE"
    assert "30,000" in veto["reason_text"] and "31,037" in veto["reason_text"]
    assert veto["ticket_risk_inr"] == pytest.approx(31037.5)
    assert "detail" not in veto
    assert desk.engine.skips[-1]["reason"] == RISK_VETO and desk.engine.skips[-1]["reason_text"] == veto["reason_text"]
    stored = led.conn.execute(
        "SELECT reason_code, intent_json FROM risk_decisions WHERE approved = 0"
    ).fetchone()
    assert stored[0] == "MAX_LOSS_PER_TRADE"
    assert json.loads(stored[1])["ticket_risk_inr"] == pytest.approx(31037.5)


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
