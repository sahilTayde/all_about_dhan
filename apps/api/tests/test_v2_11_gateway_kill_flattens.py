"""HTTP KILL is wired to the real manager/risk/router and flattens paper positions."""

from __future__ import annotations

from datetime import timedelta

from api.main import create_app
from brokers.fills import Quote
from contracts.ids import order_id
from contracts.payloads import CatastrophicStop, Decision, EntryPlan, ExitPlan, Level
from fastapi.testclient import TestClient
from oms import Account, Veto

LOCAL = ("127.0.0.1", 12345)
BASE = "http://127.0.0.1:8000"
INST = "NSE_FNO:NIFTY:2026-09-29:24400:CE"
SIG = "sg_http_kill_20260928_1001_0"


def test_v2_11_gateway_kill_flattens_paper_positions(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AAD_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("AAD_NOW", "2026-09-28T10:01:00+05:30")
    app = create_app()
    handler = app.state.v2_control
    assert handler.manager is not None and handler.risk is not None
    pm = handler.manager
    plan = EntryPlan(
        plan_id="ep_1",
        decision_id="dc_1",
        signal_id=SIG,
        account_id="founder",
        action="CHASE",
        shadow_actions=[],
        stretch={"zone_atr": 1.0, "ema20_atr": 1.0, "twap_atr": 1.0, "catastrophic_price": 140.0},
        zone="fvg",
        zone_price=24500.0,
        entry_distance_atr=1.0,
        signal_candle_atr=1.0,
        limit_price=151.40,
        est_delta=0.66,
        expires_at="2026-09-28T10:04:01+05:30",
        client_order_id=order_id("founder", SIG, "entry"),
    )
    decision = Decision(
        decision_id="dc_1",
        underlying="NIFTY",
        decision="ENTER",
        signal_ids=[SIG],
        instrument_id=INST,
        lots=1,
        lot_size=65,
        limit_price=151.40,
        shadow={"chosen": "ITM100"},
    )
    exits = ExitPlan(
        catastrophic=CatastrophicStop(level=Level(kind="premium", price=140.0)),
        time_stops=(),
        flat_by_ist="15:15",
    )
    out = pm.router.submit(plan, decision, Account("founder"), exit_plan=exits)
    assert not isinstance(out, Veto)
    clock = pm.clock
    if hasattr(clock, "advance_by"):
        clock.advance_by(timedelta(milliseconds=250))
    pm.router.broker.on_depth(
        Quote(available_ts=clock.now(), bid=151.00, ask=151.20, ltp=151.10, instrument_id=INST)
    )
    assert pm.open_book()

    client = TestClient(app, client=LOCAL, base_url=BASE)
    tok = client.post("/v2/control/confirm", json={"kind": "KILL"}).json()["confirm_token"]
    killed = client.post(
        "/v2/control/commands",
        json={"kind": "KILL", "reason": "http-panic", "confirm_token": tok, "command_id": "http-kill"},
    )
    assert killed.status_code == 200
    assert killed.json()["status"] == "applied"
    assert pm.open_book() == []
