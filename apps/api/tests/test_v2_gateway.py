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
from events.bus import MemoryBus
from events.schema import EventType
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


def test_resolve_role_token_only_never_trusts_client_role() -> None:
    from api.v2_gateway import role_from_token

    assert role_from_token("founder") == "founder"
    assert role_from_token(" FOUNDER ") == "founder"
    assert role_from_token("customer") == "customer"
    assert role_from_token("") == "customer"
    assert role_from_token(None) == "customer"
    assert role_from_token("x") == "customer"
    assert resolve_role("founder", "customer") == "customer"
    assert resolve_role("customer", "founder") == "founder"
    assert resolve_role("founder", "founder") == "founder"
    assert resolve_role("founder", "") == "customer"
    assert resolve_role("founder", None) == "customer"
    assert resolve_role(None, None) == "customer"


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
    # MemoryBus stamps Event.timestamp with live IST. ingest() refuses
    # available_ts > hub.now() (no look-ahead), so a hub frozen at TS
    # (10:01 IST on 2026-09-28) fails for the rest of that calendar day.
    later = datetime.now(IST) + timedelta(hours=1)
    hub = GatewayHub(bus, clock=_Clock(later.isoformat()))
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
    with c.websocket_connect("/v2/ws?token=customer") as ws:
        ws.send_json(
            {
                "op": "subscribe",
                "channels": ["positions", "signals:public"],
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
    with c.websocket_connect("/v2/ws?token=founder") as ws:
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
    body = c.get(
        "/v2/trace", params={"correlation_id": "corr-t", "token": "founder"}
    ).json()
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


def _leak_ui() -> dict[str, Any]:
    return {
        "board": {
            "open_trades": [{"id": "t-open", "qty": 65}],
            "closed_trades": [{"id": "t-closed"}],
            "model_signals": [{"id": "ms1"}],
            "seen_not_taken": [{"id": "snt1"}],
        },
        "founder": {"secret": True},
        "founder_book": {"rows": [1]},
        "account": {"cash": 999},
        "alerts": [{"id": "a1"}],
        "exam": {"ok": True},
        "days": [{"net": 1}],
        "health": [{"ok": True}],
        "risk_halt": False,
        "history_complete": True,
        "tape_last_ist": TS,
    }


def _signal_with_secrets() -> dict[str, Any]:
    return {
        "signal_id": "sg_acl",
        "underlying": "NIFTY",
        "side": "CE",
        "decision": "HOLD",
        "trend": "up",
        "chain_3m": {"pcr": 0.9},
        "news": "cited",
        "cited_news": ["n1"],
        "strike_choice": {
            "chosen": "ITM100",
            "reason": "LOWEST_BREAKEVEN_AT_HOLD",
            "alternatives": [{"rule": "ATM"}, {"rule": "ITM100"}],
        },
        "stop": 24400.0,
        "rsi": 71,
        "account_id": "founder",
    }


def _payload_fields(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        payload = obj.get("payload")
        if isinstance(payload, dict):
            out.update(payload)
        for value in obj.values():
            _payload_fields(value, out)
    elif isinstance(obj, list):
        for value in obj:
            _payload_fields(value, out)


def test_ws_subscribe_cannot_escalate_identity() -> None:
    """Exploit 1: in-band role/token must not replace the connect-time identity.

    Fails on the old gateway: subscribe {role:founder, token:x} after
    token=customer returned founder positions/decisions snapshots.
    """
    c, hub = _app()
    hub.ingest(_env("POSITION_UPDATE", _pos("ps_leak"), eid="2" * 32))
    with c.websocket_connect("/v2/ws?token=customer") as ws:
        ws.send_json(
            {
                "op": "subscribe",
                "role": "founder",
                "token": "x",
                "channels": ["positions", "decisions"],
            }
        )
        first = ws.receive_json()
        second = ws.receive_json()
        msgs = [first, second]
        assert any(m.get("code") == "IDENTITY_IMMUTABLE" for m in msgs)
        assert any(m.get("code") == "FORBIDDEN_CHANNEL" for m in msgs)
        denied = next(m for m in msgs if m.get("code") == "FORBIDDEN_CHANNEL")
        assert "positions" in denied["denied"]
        assert "decisions" in denied["denied"]
        assert denied["role"] == "customer"
        assert not any(m.get("op") == "snapshot" for m in msgs)
        assert not any(m.get("channel") in {"positions", "decisions"} for m in msgs)

    with c.websocket_connect("/v2/ws?role=customer") as ws:
        ws.send_json({"op": "subscribe", "role": "founder", "channels": ["positions"]})
        msgs = [ws.receive_json(), ws.receive_json()]
        assert any(m.get("code") == "IDENTITY_IMMUTABLE" for m in msgs)
        assert not any(
            m.get("op") == "snapshot" and m.get("channel") == "positions" for m in msgs
        )


def test_connect_role_query_is_not_trusted() -> None:
    c, _hub = _app()
    body = c.get(
        "/v2/snapshot", params={"role": "founder", "channels": "positions"}
    ).json()
    assert body["role"] == "customer"
    assert "positions" in body["denied"]
    with c.websocket_connect("/v2/ws?role=founder") as ws:
        ws.send_json({"op": "subscribe", "channels": ["positions"]})
        err = ws.receive_json()
        assert err.get("code") == "FORBIDDEN_CHANNEL"
        assert err["role"] == "customer"


def test_customer_snapshot_omits_legacy_founder_overlay(monkeypatch: Any) -> None:
    """Exploit 2: /v2/snapshot?token=customer must not merge board/founder/account.

    Fails on the old gateway: customer snapshot emptied positions/traces then
    merged legacy desk keys for every role.
    """
    monkeypatch.setattr("api.v2_gateway._legacy_ui", _leak_ui)
    c, _hub = _app()
    customer = c.get("/v2/snapshot", params={"token": "customer"}).json()
    assert customer["role"] == "customer"
    assert customer["positions"] == []
    assert customer["traces"] == {}
    leaked = set(customer) & {
        "board",
        "founder",
        "founder_book",
        "account",
        "alerts",
        "exam",
        "days",
        "health_rows",
        "risk_halt",
        "history_complete",
        "tape_last_ist",
    }
    assert leaked == set(), leaked
    founder = c.get("/v2/snapshot", params={"token": "founder"}).json()
    assert founder["board"]["open_trades"][0]["id"] == "t-open"
    assert founder["founder"]["secret"] is True
    assert founder["founder_book"]["rows"] == [1]
    assert founder["account"]["cash"] == 999
    assert founder["health_rows"] == [{"ok": True}]


def test_customer_trace_is_founder_only() -> None:
    """Exploit 3: /v2/trace must 403 unless the token is founder.

    Fails on the old gateway: no role check; customer received strike_choice.
    """
    c, hub = _app()
    hub.ingest(_env("SIGNAL", _signal_with_secrets(), cid="corr-acl", eid="3" * 32))
    params = {"correlation_id": "corr-acl"}
    customer = c.get("/v2/trace", params={**params, "token": "customer"})
    assert customer.status_code == 403
    assert customer.json()["detail"]["code"] == "FOUNDER_ONLY"
    missing = c.get("/v2/trace", params=params)
    assert missing.status_code == 403
    spoof = c.get("/v2/trace", params={**params, "role": "founder", "token": "x"})
    assert spoof.status_code == 403
    founder = c.get("/v2/trace", params={**params, "token": "founder"})
    assert founder.status_code == 200
    body = founder.json()
    assert body["strike_choice"]["chosen"] == "ITM100"
    assert len(body["alternatives"]) == 2


def test_customer_received_channels_and_fields_are_in_allow_list(
    monkeypatch: Any,
) -> None:
    from api.v2_gateway import (
        CUSTOMER_CHANNELS,
        CUSTOMER_SIGNAL_FIELDS,
        FOUNDER_CHANNELS,
        ROLE_ACL,
    )

    monkeypatch.setattr("api.v2_gateway._legacy_ui", _leak_ui)
    c, hub = _app()
    hub.ingest(_env("POSITION_UPDATE", _pos("ps_acl"), eid="4" * 32))
    hub.ingest(_env("SIGNAL", _signal_with_secrets(), cid="corr-pub", eid="5" * 32))
    want = ROLE_ACL["customer"]
    assert want["channels"] == CUSTOMER_CHANNELS
    assert want["signal_fields"] == CUSTOMER_SIGNAL_FIELDS
    assert want["legacy_keys"] == frozenset()
    assert want["trace"] is False
    http = c.get(
        "/v2/snapshot",
        params={
            "token": "customer",
            "channels": "positions,decisions,health,trace,signals:public",
        },
    ).json()
    extra_keys = set(http) - want["snapshot_keys"]
    assert extra_keys == set(), extra_keys
    extra_ch = set(http["channels"]) - want["channels"]
    assert extra_ch == set(), extra_ch
    fields: set[str] = set()
    _payload_fields(http, fields)
    assert fields <= want["signal_fields"], fields - want["signal_fields"]
    assert "strike_choice" not in fields
    assert "rsi" not in fields

    seen_channels: set[str] = set()
    with c.websocket_connect("/v2/ws?token=customer") as ws:
        ws.send_json(
            {
                "op": "subscribe",
                "role": "founder",
                "token": "founder",
                "channels": sorted(FOUNDER_CHANNELS | CUSTOMER_CHANNELS),
            }
        )
        msgs = [ws.receive_json() for _ in range(3)]
        hub.ingest(
            _env(
                "SIGNAL",
                {**_signal_with_secrets(), "signal_id": "sg_delta"},
                cid="corr-delta",
                eid="6" * 32,
            )
        )
        msgs.append(ws.receive_json())
    for msg in msgs:
        if "channel" in msg:
            seen_channels.add(str(msg["channel"]))
        _payload_fields(msg, fields)
    extra_ws = seen_channels - want["channels"]
    assert extra_ws == set(), extra_ws
    assert fields <= want["signal_fields"], fields - want["signal_fields"]
    assert any(
        m.get("op") == "delta" and m.get("channel") == "signals:public" for m in msgs
    )
    delta = next(m for m in msgs if m.get("op") == "delta")
    assert set(delta["envelope"]["payload"]) <= want["signal_fields"]
    assert "strike_choice" not in delta["envelope"]["payload"]
