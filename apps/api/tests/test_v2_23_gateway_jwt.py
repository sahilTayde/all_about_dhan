"""V2-23 gateway: JWT + founder 2FA fail closed; customer stays on signals:public."""

from __future__ import annotations

from typing import Any

from api.gateway_auth import JWT_ENV, TOTP_ENV
from api.main import create_app
from api.v2_gateway import ROLE_ACL
from auth import (
    CUSTOMER_CHANNELS as AUTH_CUSTOMER,
)
from auth import (
    CUSTOMER_SIGNAL_FIELDS as AUTH_FIELDS,
)
from auth import (
    FOUNDER_CHANNELS as AUTH_FOUNDER,
)
from auth import (
    issue_access,
    issue_refresh,
    totp_at,
)
from fastapi.testclient import TestClient

JWT = "paper-test-hmac-not-a-production-key"
RFC_SEED = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
NOW = 1_700_000_000.0
BASE = "http://127.0.0.1:8000"
REMOTE = ("203.0.113.10", 9)
LOCAL = ("127.0.0.1", 50000)


def _app(monkeypatch: Any, *, remote: bool = True) -> TestClient:
    monkeypatch.setenv(JWT_ENV, JWT)
    monkeypatch.setenv(TOTP_ENV, RFC_SEED)
    monkeypatch.setenv("AAD_NOW", "2023-11-14T22:13:20+00:00")
    app = create_app()
    client = REMOTE if remote else LOCAL
    return TestClient(app, base_url=BASE, client=client)


def _tok(*, role: str, tfa: bool = False, sub: str | None = None) -> str:
    return issue_access(
        JWT,
        role=role,
        sub=sub or role,
        now=NOW,
        tfa=tfa,
        totp_secret=RFC_SEED,
        totp_code=totp_at(RFC_SEED, NOW) if tfa else "",
    )


def test_acl_matches_auth_package() -> None:
    assert ROLE_ACL["customer"]["channels"] == AUTH_CUSTOMER
    assert ROLE_ACL["founder"]["channels"] == AUTH_FOUNDER
    assert ROLE_ACL["customer"]["signal_fields"] == AUTH_FIELDS
    assert "signals:public" in ROLE_ACL["founder"]["channels"]


def test_jwt_required_unauth_and_query_fail_closed(monkeypatch: Any) -> None:
    c = _app(monkeypatch)
    missing = c.get("/v2/snapshot")
    assert missing.status_code == 401
    assert missing.json()["detail"]["code"] == "UNAUTHORIZED"
    query = c.get(
        "/v2/snapshot", params={"access_token": _tok(role="founder", tfa=True)}
    )
    assert query.status_code == 401
    assert query.json()["detail"]["code"] == "QUERY_TOKEN_REFUSED"
    expired = c.get(
        "/v2/snapshot",
        headers={"Authorization": f"Bearer {_tok(role='customer')}"},
    )
    # AAD_NOW matches NOW; token is valid here. Expired is the library test.
    assert expired.status_code == 200
    assert expired.json()["role"] == "customer"


def test_customer_jwt_public_only_and_no_control(monkeypatch: Any) -> None:
    c = _app(monkeypatch)
    hdr = {"Authorization": f"Bearer {_tok(role='customer')}"}
    snap = c.get(
        "/v2/snapshot", headers=hdr, params={"channels": "positions,signals:public"}
    )
    assert snap.status_code == 200
    body = snap.json()
    assert body["role"] == "customer"
    assert "positions" in body["denied"]
    assert "signals:public" in body["channels"]
    assert c.get("/v2/control", headers=hdr).status_code == 403
    start = c.post(
        "/v2/control/commands",
        headers=hdr,
        json={"kind": "START", "reason": "nope", "command_id": "cust-1"},
    )
    assert start.status_code == 403
    assert start.json()["detail"]["code"] == "FOUNDER_ONLY"


def test_founder_jwt_needs_2fa_for_control(monkeypatch: Any) -> None:
    c = _app(monkeypatch)
    no_tfa = {"Authorization": f"Bearer {_tok(role='founder', tfa=False)}"}
    snap = c.get("/v2/snapshot", headers=no_tfa, params={"channels": "positions"})
    assert snap.status_code == 200
    assert snap.json()["role"] == "founder"
    assert "positions" in snap.json()["channels"]
    denied = c.get("/v2/control", headers=no_tfa)
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "TFA_REQUIRED"
    hdr = {"Authorization": f"Bearer {_tok(role='founder', tfa=True)}"}
    surface = c.get("/v2/control", headers=hdr)
    assert surface.status_code == 200
    assert surface.json()["stub"] is False
    start = c.post(
        "/v2/control/commands",
        headers=hdr,
        json={"kind": "START", "reason": "jwt-tfa", "command_id": "jwt-start"},
    )
    assert start.status_code == 200
    assert start.json()["applied"] is True


def test_refresh_jwt_is_forbidden(monkeypatch: Any) -> None:
    c = _app(monkeypatch)
    refresh = issue_refresh(JWT, role="founder", sub="founder", now=NOW)
    r = c.get("/v2/snapshot", headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "REFRESH_FORBIDDEN"


def test_jwt_rest_rate_limit(monkeypatch: Any) -> None:
    c = _app(monkeypatch)
    hdr = {"Authorization": f"Bearer {_tok(role='customer')}"}
    codes = [c.get("/v2/snapshot", headers=hdr).status_code for _ in range(11)]
    assert 200 in codes
    assert 429 in codes


def test_ws_customer_jwt_cannot_take_founder_channel(monkeypatch: Any) -> None:
    c = _app(monkeypatch)
    token = _tok(role="customer")
    with c.websocket_connect(
        "/v2/ws",
        headers={"Host": "127.0.0.1:8000", "Authorization": f"Bearer {token}"},
    ) as ws:
        ws.send_json({"op": "subscribe", "channels": ["positions", "signals:public"]})
        msgs = [ws.receive_json(), ws.receive_json()]
        ops = {m.get("op") for m in msgs}
        assert "error" in ops
        denied = next(m for m in msgs if m.get("op") == "error")
        assert denied["code"] == "FORBIDDEN_CHANNEL"
        assert "positions" in denied["denied"]
        snap = next(m for m in msgs if m.get("op") == "snapshot")
        assert snap["channel"] == "signals:public"
