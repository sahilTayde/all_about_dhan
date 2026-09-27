"""V2-13 acceptance: snapshot + ordered deltas, gap resync, role scope, REG-04c, stubs."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from api.main import create_app
from api.v2_gateway import (
    CONTROL_FLAG,
    CONTROL_KINDS,
    IST,
    GatewayHub,
    WsClient,
    envelope_from_parts,
    ist_iso,
    resolve_role,
)
from contracts.clock import SimClock
from contracts.envelope import Envelope
from events.bus import MemoryBus  # type: ignore[import-untyped]
from events.schema import EventType  # type: ignore[import-untyped]
from fastapi.testclient import TestClient

TS = "2026-09-28T10:01:00.000+05:30"
LATER = "2026-09-28T10:01:01.000+05:30"
FUTURE = "2026-09-28T10:05:00.000+05:30"


class _Clock:
    def __init__(self, now: str = TS) -> None:
        self._now = datetime.fromisoformat(now)

    def now(self) -> datetime:
        return self._now

    def set(self, raw: str) -> None:
        self._now = datetime.fromisoformat(raw)


def _env(
    kind: str,
    payload: dict[str, Any],
    *,
    available: str = TS,
    cid: str | None = None,
    eid: str = "a" * 32,
) -> Envelope:
    return envelope_from_parts(
        kind, payload, available_ts=available, correlation_id=cid, event_id=eid
    )


def _pos(pid: str, qty: int = 65) -> dict[str, Any]:
    return {
        "position_id": pid,
        "account_id": "founder",
        "instrument_id": "NSE_FNO:NIFTY:2026-09-29:24400:CE",
        "net_qty": qty,
        "avg_price": 151.35,
        "mark": 153.1,
        "unrealized_inr": 113.75,
        "stop": {"kind": "underlying", "price": 24488.0},
        "protective_order": None,
        "strategy_id": "R8-E1-COIL-SIDE",
    }


def test_resolve_role_customer_token_cannot_be_founder() -> None:
    assert resolve_role("founder", "customer") == "customer"
    assert resolve_role("customer", "founder") == "customer"
    assert resolve_role("founder", "founder") == "founder"


def test_ist_iso_offset() -> None:
    text = ist_iso(datetime(2026, 9, 28, 10, 1, tzinfo=IST))
    assert text.endswith("+05:30")
    assert "T" in text


def test_no_lookahead_refuses_future_available_ts() -> None:
    hub = GatewayHub(clock=_Clock(TS))
    assert (
        hub.ingest(_env("POSITION_UPDATE", _pos("ps_future"), available=FUTURE)) is None
    )
    assert hub.positions() == []


def test_reg04c_snapshot_lists_every_ledger_open_position() -> None:
    """REG-04c: UI snapshot lists every ledger-open position."""
    rows = [_pos("ps_a"), _pos("ps_b", qty=130), _pos("ps_c", qty=195)]
    hub = GatewayHub(clock=_Clock(TS), ledger_open=rows)
    snap = hub.snapshot(["positions"], "founder")
    ids = {p["position_id"] for p in snap["positions"]}
    assert ids == {"ps_a", "ps_b", "ps_c"}
    assert {p["position_id"] for p in snap["channels"]["positions"]["items"]} == ids


def test_ingest_from_memory_bus() -> None:
    bus = MemoryBus()
    hub = GatewayHub(bus, clock=_Clock(TS))
    bus.publish(EventType.POSITION_UPDATE, _pos("ps_bus"), source="desk")
    assert any(p["position_id"] == "ps_bus" for p in hub.positions())


def test_trace_includes_strike_choice_and_alternatives() -> None:
    hub = GatewayHub(clock=_Clock(TS))
    choice = {
        "chosen": "ITM100",
        "reason": "LOWEST_BREAKEVEN_AT_HOLD",
        "rule_version": "router-1.0.0",
        "alternatives": [
            {"rule": "ATM", "instrument_id": "NSE_FNO:NIFTY:2026-09-29:24500:CE"},
            {"rule": "ITM100", "instrument_id": "NSE_FNO:NIFTY:2026-09-29:24400:CE"},
        ],
    }
    hub.ingest(
        _env(
            "SIGNAL",
            {
                "signal_id": "sg_1",
                "underlying": "NIFTY",
                "side": "CE",
                "strike_choice": choice,
            },
            cid="dc_1",
            eid="b" * 32,
        )
    )
    row = hub.traces["dc_1"]
    assert row["strike_choice"]["chosen"] == "ITM100"
    assert len(row["alternatives"]) == 2


def _app() -> tuple[TestClient, GatewayHub]:
    app = create_app()
    hub: GatewayHub = app.state.v2_hub
    hub.clock = _Clock(TS)
    return TestClient(app), hub


def test_legacy_readonly_routes_still_work() -> None:
    c, _hub = _app()
    assert c.get("/health").json()["ok"] is True
    assert c.get("/ui/snapshot").status_code == 200
    assert c.get("/paper/signal").status_code == 200
    assert "paper_signal" in c.get("/paper/live-signals").json().get(
        "kind", "paper_signal"
    )
    assert c.get("/v2/snapshot").json()["v2"] is True
    assert c.get("/v2/snapshot").json()["orders"] == "REFUSED"


def test_customer_cannot_subscribe_founder_channels() -> None:
    c, _hub = _app()
    r = c.get(
        "/v2/snapshot",
        params={
            "role": "customer",
            "token": "customer",
            "channels": "positions,decisions,health",
        },
    )
    body = r.json()
    assert body["role"] == "customer"
    assert body["denied"] == ["positions", "decisions", "health"]
    assert body["channels"] == {}
    assert body["positions"] == []
    with c.websocket_connect("/v2/ws?role=customer&token=customer") as ws:
        ws.send_json(
            {
                "op": "subscribe",
                "channels": ["positions", "signals:public"],
                "role": "customer",
                "token": "customer",
            }
        )
        denied = ws.receive_json()
        pub = ws.receive_json()
        msgs = [denied, pub]
        err = next(m for m in msgs if m.get("code") == "FORBIDDEN_CHANNEL")
        assert "positions" in err["denied"]
        snap = next(m for m in msgs if m.get("op") == "snapshot")
        assert snap["channel"] == "signals:public"


def _drain(client: WsClient) -> list[dict[str, Any]]:
    import queue as _q

    out: list[dict[str, Any]] = []
    while True:
        try:
            out.append(client.outbound.get_nowait())
        except _q.Empty:
            return out


def test_ws_snapshot_then_ordered_deltas() -> None:
    clock = _Clock(TS)
    hub = GatewayHub(clock=clock)
    client = hub.connect(role="founder")
    hub.subscribe(client, ["positions"])
    hello = _drain(client)
    assert hello[0]["op"] == "snapshot" and hello[0]["seq"] == 0
    hub.ingest(_env("POSITION_UPDATE", _pos("ps_1"), eid="c" * 32))
    clock.set(LATER)
    hub.ingest(_env("POSITION_UPDATE", _pos("ps_2"), available=LATER, eid="d" * 32))
    deltas = _drain(client)
    assert [m["op"] for m in deltas] == ["delta", "delta"]
    assert [m["seq"] for m in deltas] == [1, 2]
    assert deltas[0]["channel"] == "positions"
    assert deltas[0]["as_of"].endswith("+05:30")
    c, _hub = _app()
    with c.websocket_connect("/v2/ws?role=founder") as ws:
        ws.send_json({"op": "subscribe", "channels": ["positions"]})
        assert ws.receive_json()["op"] == "snapshot"


def test_ws_resync_after_planted_gap() -> None:
    clock = _Clock(TS)
    hub = GatewayHub(clock=clock)
    client = hub.connect(role="founder")
    hub.subscribe(client, ["positions"])
    assert _drain(client)[0]["op"] == "snapshot"
    hub.ingest(_env("POSITION_UPDATE", _pos("ps_1"), eid="e" * 32))
    assert _drain(client)[0]["seq"] == 1
    client.suppress.add(2)
    clock.set(LATER)
    hub.ingest(_env("POSITION_UPDATE", _pos("ps_2"), available=LATER, eid="f" * 32))
    assert _drain(client) == []
    later2 = "2026-09-28T10:01:02.000+05:30"
    clock.set(later2)
    hub.ingest(_env("POSITION_UPDATE", _pos("ps_3"), available=later2, eid="1" * 32))
    gap = _drain(client)
    assert gap[0]["op"] == "delta" and gap[0]["seq"] == 3
    hub.resync(client, "positions")
    again = _drain(client)[0]
    assert again["op"] == "snapshot" and again.get("resync") is True
    assert again["seq"] == 3
    ids = {p["position_id"] for p in again["data"]["items"]}
    assert ids == {"ps_1", "ps_2", "ps_3"}


def test_control_routes_are_stub(monkeypatch: Any) -> None:
    c, _hub = _app()
    surface = c.get("/v2/control").json()
    assert (
        surface["stub"] is True
        and surface["ticket"] == "V2-11"
        and surface["implemented"] is False
    )
    assert surface["kinds"] == list(CONTROL_KINDS)
    assert c.post("/v2/control/commands", json={"kind": "KILL"}).status_code == 501
    monkeypatch.setenv(CONTROL_FLAG, "1")
    flagged = c.get("/v2/control").json()
    assert flagged["enabled"] is True and flagged["implemented"] is False
    refused = c.post("/v2/control/commands", json={"kind": "START", "args": {}})
    assert refused.status_code == 501
    assert refused.json()["detail"]["applied"] is False


def test_v2_trace_route_strike_choice() -> None:
    c, hub = _app()
    hub.ingest(
        _env(
            "SIGNAL",
            {
                "signal_id": "sg_t",
                "underlying": "NIFTY",
                "side": "CE",
                "strike_choice": {
                    "chosen": "ITM100",
                    "reason": "LOWEST_BREAKEVEN_AT_HOLD",
                    "alternatives": [{"rule": "ATM"}, {"rule": "ITM100"}],
                },
            },
            cid="corr-t",
            eid="9" * 32,
        )
    )
    body = c.get("/v2/trace", params={"correlation_id": "corr-t"}).json()
    assert body["ok"] is True
    assert body["strike_choice"]["chosen"] == "ITM100"
    assert len(body["alternatives"]) == 2
    assert body["steps"][0]["fields"]["strike_choice"]["chosen"] == "ITM100"


def test_simclock_no_backward() -> None:
    clock = SimClock(datetime.fromisoformat(TS))
    clock.advance_by(timedelta(seconds=1))
    try:
        clock.advance_to(datetime.fromisoformat(TS))
    except ValueError as exc:
        assert "backwards" in str(exc)
    else:
        raise AssertionError("expected look-ahead / backward refusal")
