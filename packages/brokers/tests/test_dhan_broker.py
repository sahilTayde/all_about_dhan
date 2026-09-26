"""DhanBroker against a mocked HTTP layer (httpx.MockTransport). No request leaves this process.

Payloads are asserted against https://dhanhq.co/docs/v2/orders/, /super-order/, /portfolio/, /funds/.
"""

import itertools
import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pytest
import yaml

from brokers import LiveOrderRefused, OrderState, Position, exit_intent
from brokers.dhan import DhanBroker
from dhan_client.config import Credentials, Settings
from dhan_client.errors import DhanApiError
from dhan_client.rest import RestClient
from risk_engine import IST, LIVE_CONFIRM_ENV, LIVE_CONFIRM_VALUE, RiskDecision, TradeIntent

REPO = Path(__file__).resolve().parents[3]
CLIENT = "1000000001"


class FakeDhan:
    """Records every request; answers with docs-shaped JSON. Raise an exception to simulate no response."""

    def __init__(self):
        self.requests = []
        self.responses = {}

    def __call__(self, request):
        assert request.url.host == "api.dhan.co" and request.url.path.startswith("/v2/")
        body = json.loads(request.content) if request.content else None
        self.requests.append((request.method, request.url.path, body, request.headers))
        status, payload = self.responses.get((request.method, request.url.path), (200, {"orderId": "5001", "orderStatus": "PENDING"}))
        if isinstance(payload, Exception):
            raise payload
        return httpx.Response(status, json=payload)

    @property
    def calls(self):
        return [(m, p, b) for m, p, b, _ in self.requests]


def make(tmp_path, mode="limited_live", *, dry_run=False):
    path = tmp_path / "risk_limits.yaml"
    path.unlink(missing_ok=True)
    if mode is not None:
        cfg = yaml.safe_load((REPO / "config" / "risk_limits.yaml").read_text())
        path.write_text(yaml.safe_dump({**cfg, "mode": mode}))
    fake = FakeDhan()
    creds = Credentials(client_id="" if dry_run else CLIENT, access_token="" if dry_run else "FAKE-TOKEN")
    rest = RestClient(Settings(credentials=creds, dry_run=dry_run))
    rest._http = httpx.Client(transport=httpx.MockTransport(fake))
    broker = DhanBroker(rest, config_path=path)
    broker.fake = fake
    return broker


def ok(cid, action="ENTRY", ts=None):
    return RiskDecision(True, cid, action, "OK", "test", ts or datetime.now(IST))


def intent(**kw):
    base = dict(symbol="NIFTY 25000 CE", side="BUY", lots=1, lot_size=65, instrument_id="43210",
                exchange="NSE_FNO", product_type="INTRADAY", decision_price=100.0)
    return TradeIntent(**{**base, **kw})


@pytest.fixture
def live_env(monkeypatch):
    monkeypatch.setenv(LIVE_CONFIRM_ENV, LIVE_CONFIRM_VALUE)


# ------------------------------------------------------------ live gate

MODES = ["paper", "shadow", "limited_live", "live", "bogus", None]  # None = config file missing
ENVS = [None, "", "yes", "i_understand_real_money", " I_UNDERSTAND_REAL_MONEY", LIVE_CONFIRM_VALUE]
DECISIONS = ["none", "vetoed", "other_order", "wrong_action", "stale", "approved"]


def decision_for(kind, cid):
    return {
        "none": None,
        "vetoed": RiskDecision(False, cid, "ENTRY", "MAX_LOTS", "veto", datetime.now(IST)),
        "other_order": ok("someone-else"),
        "wrong_action": ok(cid, "EXIT"),
        "stale": ok(cid, ts=datetime.now(IST) - timedelta(minutes=2)),
        "approved": ok(cid),
    }[kind]


@pytest.mark.parametrize("mode", MODES, ids=str)
def test_refuses_every_combination_except_all_three_true(tmp_path, monkeypatch, mode):
    sent = 0
    for env, kind in itertools.product(ENVS, DECISIONS):
        if env is None:
            monkeypatch.delenv(LIVE_CONFIRM_ENV, raising=False)
        else:
            monkeypatch.setenv(LIVE_CONFIRM_ENV, env)
        broker, it = make(tmp_path, mode), intent()
        allowed = mode in ("limited_live", "live") and env == LIVE_CONFIRM_VALUE and kind == "approved"
        if allowed:
            assert broker.place_order(it, decision_for(kind, it.client_order_id)).state == OrderState.SUBMITTED
            assert len(broker.fake.calls) == 1
            sent += 1
        else:
            with pytest.raises(LiveOrderRefused):
                broker.place_order(it, decision_for(kind, it.client_order_id))
            assert broker.fake.calls == [], (mode, env, kind)
            assert broker.orders == {}
    assert sent == (1 if mode in ("limited_live", "live") else 0)


def test_refuses_without_credentials_even_if_gate_open(tmp_path, live_env):
    broker, it = make(tmp_path, dry_run=True), intent()
    with pytest.raises(LiveOrderRefused, match="credentials"):
        broker.place_order(it, ok(it.client_order_id))


@pytest.mark.parametrize("op", ["super", "modify", "cancel", "exit", "flatten"])
def test_every_mutating_call_goes_through_the_gate(tmp_path, monkeypatch, op, caplog):
    monkeypatch.setenv(LIVE_CONFIRM_ENV, LIVE_CONFIRM_VALUE)
    broker = make(tmp_path)
    order = broker.place_order(e := intent(order_type="LIMIT", price=99.0), ok(e.client_order_id))
    cid = order.client_order_id
    ex = exit_intent(Position("NIFTY 25000 CE", 65, 100.0, "43210"), exit_reason="MANUAL")
    run = {
        "super": lambda d: broker.place_super_order(s := intent(target=130.0, stop_loss=90.0), d(s.client_order_id, "ENTRY")),
        "modify": lambda d: broker.modify_order(order, d(cid, "MODIFY"), price=98.0),
        "cancel": lambda d: broker.cancel_order(order, d(cid, "CANCEL")),
        "exit": lambda d: broker.exit_position(ex, d(ex.client_order_id, "EXIT")),
        "flatten": lambda d: broker.flatten_all(d("FLATTEN_ALL", "FLATTEN")),
    }[op]
    broker.fake.responses[("DELETE", "/v2/positions")] = (200, {"status": "SUCCESS", "message": "done"})
    before = len(broker.fake.calls)
    monkeypatch.delenv(LIVE_CONFIRM_ENV)
    with pytest.raises(LiveOrderRefused):
        run(ok)
    assert len(broker.fake.calls) == before and "LIVE ORDER REFUSED" in caplog.text
    monkeypatch.setenv(LIVE_CONFIRM_ENV, LIVE_CONFIRM_VALUE)
    with pytest.raises(LiveOrderRefused):  # gate open but risk vetoed
        run(lambda c, a: RiskDecision(False, c, a, "KILL_SWITCH", "veto", datetime.now(IST)))
    assert len(broker.fake.calls) == before
    run(ok)
    assert len(broker.fake.calls) == before + 1


# ------------------------------------------------------------- payloads

def base_body(it):
    return {"dhanClientId": CLIENT, "correlationId": it.client_order_id, "transactionType": it.side,
            "exchangeSegment": "NSE_FNO", "productType": "INTRADAY", "securityId": "43210", "quantity": it.qty}


@pytest.mark.parametrize(
    "kw,extra",
    [
        ({}, {"orderType": "MARKET", "price": 0.0}),
        ({"order_type": "LIMIT", "price": 99.5}, {"orderType": "LIMIT", "price": 99.5}),
        ({"order_type": "SL", "price": 94.0, "trigger_price": 95.0, "side": "SELL", "purpose": "EXIT"},
         {"orderType": "STOP_LOSS", "price": 94.0, "triggerPrice": 95.0}),
        ({"order_type": "SL-M", "trigger_price": 95.0, "side": "SELL", "purpose": "EXIT"},
         {"orderType": "STOP_LOSS_MARKET", "price": 0.0, "triggerPrice": 95.0}),
    ],
    ids=["market", "limit", "sl", "sl-m"],
)
def test_place_order_payload(tmp_path, live_env, kw, extra):
    broker, it = make(tmp_path), intent(lots=2, **kw)
    order = broker.place_order(it, ok(it.client_order_id, broker.action_for(it)))
    ((method, path, body, headers),) = broker.fake.requests
    assert (method, path) == ("POST", "/v2/orders")
    assert body == {**base_body(it), "validity": "DAY", "afterMarketOrder": False, **extra}
    assert body["quantity"] == 130
    assert headers["access-token"] == "FAKE-TOKEN" and headers["client-id"] == CLIENT
    assert order.broker_order_id == "5001" and order.state == OrderState.SUBMITTED
    assert [h["to"] for h in order.history] == ["SUBMITTED"]


def test_super_order_payload(tmp_path, live_env):
    broker = make(tmp_path)
    it = intent(order_type="LIMIT", price=100.0, target=130.0, stop_loss=90.0, trailing_jump=5.0)
    order = broker.place_super_order(it, ok(it.client_order_id))
    assert broker.fake.calls == [("POST", "/v2/super/orders", {
        **base_body(it), "orderType": "LIMIT", "price": 100.0, "targetPrice": 130.0,
        "stopLossPrice": 90.0, "trailingJump": 5.0,
    })]
    assert order.is_super


def test_modify_payloads_target_shift_and_trailing_sl(tmp_path, live_env):
    broker = make(tmp_path)
    it = intent(order_type="LIMIT", price=100.0, target=130.0, stop_loss=90.0, trailing_jump=5.0)
    sup = broker.place_super_order(it, ok(it.client_order_id))
    sup.state = OrderState.FILLED  # entry done: only target / stop legs may change
    broker.modify_order(sup, ok(it.client_order_id, "MODIFY"), target=140.0)
    broker.modify_order(sup, ok(it.client_order_id, "MODIFY"), stop_loss=105.0)
    head = {"dhanClientId": CLIENT, "orderId": "5001"}
    assert broker.fake.calls[1:] == [
        ("PUT", "/v2/super/orders/5001", {**head, "legName": "TARGET_LEG", "targetPrice": 140.0}),
        ("PUT", "/v2/super/orders/5001", {**head, "legName": "STOP_LOSS_LEG", "stopLossPrice": 105.0, "trailingJump": 5.0}),
    ]
    assert (sup.target, sup.stop_loss) == (140.0, 105.0)

    stop = intent(order_type="SL-M", trigger_price=95.0, side="SELL", purpose="EXIT", exit_reason="STOP_HIT")
    order = broker.place_order(stop, ok(stop.client_order_id, "EXIT"))
    broker.modify_order(order, ok(stop.client_order_id, "MODIFY"), trigger_price=97.0)  # manual trailing SL
    assert broker.fake.calls[-1] == ("PUT", "/v2/orders/5001", {
        **head, "orderType": "STOP_LOSS_MARKET", "legName": "", "quantity": 65, "price": 0.0,
        "validity": "DAY", "triggerPrice": 97.0,
    })


def test_modify_pending_super_entry_uses_entry_leg(tmp_path, live_env):
    broker = make(tmp_path)
    it = intent(order_type="LIMIT", price=100.0, target=130.0, stop_loss=90.0)
    sup = broker.place_super_order(it, ok(it.client_order_id))
    broker.modify_order(sup, ok(it.client_order_id, "MODIFY"), price=99.0)
    assert broker.fake.calls[-1] == ("PUT", "/v2/super/orders/5001", {
        "dhanClientId": CLIENT, "orderId": "5001", "orderType": "LIMIT", "legName": "ENTRY_LEG",
        "quantity": 65, "price": 99.0, "targetPrice": 130.0, "stopLossPrice": 90.0, "trailingJump": 0.0,
    })


def test_cancel_exit_and_flatten_payloads(tmp_path, live_env):
    broker = make(tmp_path)
    broker.fake.responses[("DELETE", "/v2/orders/5001")] = (202, {"orderId": "5001", "orderStatus": "CANCELLED"})
    broker.fake.responses[("DELETE", "/v2/super/orders/5001/ENTRY_LEG")] = (202, {"orderId": "5001", "orderStatus": "CANCELLED"})
    broker.fake.responses[("DELETE", "/v2/positions")] = (200, {"status": "SUCCESS", "message": "All orders and positions exited successfully"})

    reg = broker.place_order(a := intent(order_type="LIMIT", price=90.0), ok(a.client_order_id))
    broker.cancel_order(reg, ok(a.client_order_id, "CANCEL"), reason="TIMEOUT_UNFILLED")
    assert reg.state == OrderState.CANCELLED and reg.cancel_reason == "TIMEOUT_UNFILLED"

    sup = broker.place_super_order(b := intent(target=130.0, stop_loss=90.0), ok(b.client_order_id))
    broker.cancel_order(sup, ok(b.client_order_id, "CANCEL"))

    ex = exit_intent(Position("NIFTY 25000 CE", 65, 100.0, "43210"), exit_reason="TARGET_HIT", decision_price=130.0)
    broker.exit_position(ex, ok(ex.client_order_id, "EXIT"))
    resp = broker.flatten_all(ok("FLATTEN_ALL", "FLATTEN"))

    calls = [(m, p) for m, p, _ in broker.fake.calls]
    assert calls == [
        ("POST", "/v2/orders"), ("DELETE", "/v2/orders/5001"),
        ("POST", "/v2/super/orders"), ("DELETE", "/v2/super/orders/5001/ENTRY_LEG"),
        ("POST", "/v2/orders"), ("DELETE", "/v2/positions"),
    ]
    assert broker.fake.calls[4][2] == {
        "dhanClientId": CLIENT, "correlationId": ex.client_order_id, "transactionType": "SELL",
        "exchangeSegment": "NSE_FNO", "productType": "INTRADAY", "securityId": "43210", "quantity": 65,
        "orderType": "MARKET", "validity": "DAY", "afterMarketOrder": False, "price": 0.0,
    }
    assert broker.fake.calls[1][2] is None and broker.fake.calls[5][2] is None  # no body on DELETE
    assert resp["status"] == "SUCCESS"


# ------------------------------------------ status, idempotency, errors

def test_order_status_drives_partial_then_filled(tmp_path, live_env):
    broker = make(tmp_path)
    order = broker.place_order(it := intent(lots=2), ok(it.client_order_id))
    path = "/v2/orders/5001"
    broker.fake.responses[("GET", path)] = (200, {"orderId": "5001", "orderStatus": "PART_TRADED", "filledQty": 65, "averageTradedPrice": 100.0})
    broker.get_order_status(order)
    assert order.state == OrderState.PARTIAL and order.filled_qty == 65
    broker.fake.responses[("GET", path)] = (200, {"orderId": "5001", "orderStatus": "TRADED", "filledQty": 130, "averageTradedPrice": 101.0})
    broker.get_order_status(order)
    assert order.state == OrderState.FILLED and order.avg_fill_price == 101.0
    assert [h["to"] for h in order.history] == ["SUBMITTED", "PARTIAL", "FILLED"]


def test_broker_side_cancel_and_expiry_are_mapped(tmp_path, live_env):
    broker = make(tmp_path)
    a = broker.place_order(x := intent(), ok(x.client_order_id))
    broker.fake.responses[("GET", "/v2/orders/5001")] = (200, {"orderId": "5001", "orderStatus": "CANCELLED", "filledQty": 0})
    broker.get_order_status(a)
    assert a.state == OrderState.CANCELLED and a.cancel_reason == "BROKER_CANCELLED"
    b = broker.place_order(y := intent(), ok(y.client_order_id))
    broker.fake.responses[("GET", "/v2/orders/5001")] = (200, {"orderId": "5001", "orderStatus": "EXPIRED", "filledQty": 0})
    broker.get_order_status(b)
    assert b.state == OrderState.EXPIRED


def test_http_rejection_marks_order_rejected(tmp_path, live_env):
    broker = make(tmp_path)
    broker.fake.responses[("POST", "/v2/orders")] = (400, {"errorType": "Order_Error", "errorCode": "DH-906", "errorMessage": "Invalid quantity"})
    order = broker.place_order(it := intent(), ok(it.client_order_id))
    assert order.state == OrderState.REJECTED and "DH-906" in order.history[-1]["reason"]


def test_same_client_order_id_is_sent_once(tmp_path, live_env):
    broker, it = make(tmp_path), intent()
    first = broker.place_order(it, ok(it.client_order_id))
    assert broker.place_order(it, ok(it.client_order_id)) is first
    assert len(broker.fake.calls) == 1


def test_lost_response_looks_up_correlation_id_before_resending(tmp_path, live_env):
    broker, it = make(tmp_path), intent()
    broker.fake.responses[("POST", "/v2/orders")] = (0, httpx.ConnectError("timeout"))
    with pytest.raises(DhanApiError):
        broker.place_order(it, ok(it.client_order_id))
    lookup = f"/v2/orders/external/{it.client_order_id}"
    broker.fake.responses[("GET", lookup)] = (200, {"orderId": "7777", "orderStatus": "PENDING", "filledQty": 0})
    order = broker.place_order(it, ok(it.client_order_id))
    assert order.broker_order_id == "7777" and order.state == OrderState.SUBMITTED
    assert [(m, p) for m, p, _ in broker.fake.calls] == [("POST", "/v2/orders"), ("GET", lookup)]  # no 2nd POST


def test_lookup_failure_never_resends(tmp_path, live_env):
    broker, it = make(tmp_path), intent()
    broker.fake.responses[("POST", "/v2/orders")] = (0, httpx.ConnectError("timeout"))
    with pytest.raises(DhanApiError):
        broker.place_order(it, ok(it.client_order_id))
    broker.fake.responses[("GET", f"/v2/orders/external/{it.client_order_id}")] = (500, {"errorMessage": "down"})
    with pytest.raises(DhanApiError, match="not resending"):
        broker.place_order(it, ok(it.client_order_id))
    assert [m for m, _, _ in broker.fake.calls] == ["POST", "GET"]


def test_invalid_intents_rejected_before_any_call(tmp_path, live_env):
    broker = make(tmp_path)
    for bad in (intent(instrument_id=""), intent(order_type="LIMIT"), intent(client_order_id="x" * 31)):
        with pytest.raises(ValueError):
            broker.place_order(bad, ok(bad.client_order_id))
    assert broker.fake.calls == []


def test_reads_parse_docs_shapes(tmp_path):
    broker = make(tmp_path, "paper")  # reads are not orders: allowed in any mode
    broker.fake.responses[("GET", "/v2/positions")] = (200, [
        {"tradingSymbol": "NIFTY-Sep2026-25000-CE", "securityId": "43210", "positionType": "LONG",
         "exchangeSegment": "NSE_FNO", "productType": "INTRADAY", "buyAvg": 100.5, "netQty": 65, "costPrice": 100.5},
        {"tradingSymbol": "OLD", "securityId": "1", "positionType": "CLOSED", "netQty": 0},
    ])
    broker.fake.responses[("GET", "/v2/orders")] = (200, [
        {"orderId": "5001", "correlationId": "aadabc", "orderStatus": "PART_TRADED", "filledQty": 30, "tradingSymbol": "X"},
    ])
    broker.fake.responses[("GET", "/v2/fundlimit")] = (200, {"dhanClientId": CLIENT, "availabelBalance": 98440.0, "sodLimit": 113642})
    assert broker.get_positions() == [Position("NIFTY-Sep2026-25000-CE", 65, 100.5, "43210")]
    (snap,) = broker.get_orders()
    assert (snap.client_order_id, snap.state, snap.filled_qty) == ("aadabc", OrderState.PARTIAL, 30)
    assert broker.get_balance() == 98440.0
