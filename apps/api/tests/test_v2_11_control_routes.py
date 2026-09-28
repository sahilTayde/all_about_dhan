"""routes are localhost-only unless auth is on (V2-13)"""

from __future__ import annotations

from api.gateway_auth import CommandRateLimiter
from api.main import create_app
from fastapi.testclient import TestClient

LOCAL = ("127.0.0.1", 12345)
REMOTE = ("203.0.113.10", 9)
BASE = "http://127.0.0.1:8000"


def _local() -> TestClient:
    app = create_app()
    app.state.v2_limiter = CommandRateLimiter(per_s=100)
    return TestClient(app, client=LOCAL, base_url=BASE)


def _remote() -> TestClient:
    app = create_app()
    app.state.v2_limiter = CommandRateLimiter(per_s=100)
    return TestClient(app, client=REMOTE, base_url=BASE)


def test_v2_11_routes_localhost_unless_auth() -> None:
    remote = _remote()
    assert remote.get("/v2/control").status_code == 403
    assert remote.post("/v2/control/commands", json={"kind": "START", "reason": "x"}).status_code == 403
    authed = remote.get("/v2/control", params={"token": "founder"})
    assert authed.status_code == 200
    body = authed.json()
    assert body["implemented"] is True and body["stub"] is False
    assert "START" in body["kinds"]
    customer = remote.get("/v2/control", params={"token": "customer"})
    assert customer.status_code == 403
    local = _local()
    assert local.get("/v2/control").status_code == 200
    start = local.post("/v2/control/commands", json={"kind": "START", "reason": "local", "command_id": "loc-1"})
    assert start.status_code == 200
    assert start.json()["status"] == "applied"
    kill = local.post("/v2/control/commands", json={"kind": "KILL", "reason": "no-token"})
    assert kill.status_code == 422
    tok = local.post("/v2/control/confirm", json={"kind": "KILL"}).json()["confirm_token"]
    ok = local.post(
        "/v2/control/commands",
        json={"kind": "KILL", "reason": "panic", "confirm_token": tok, "command_id": "k-loc"},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "applied"
    reuse = local.post(
        "/v2/control/commands",
        json={"kind": "KILL", "reason": "again", "confirm_token": tok, "command_id": "k-2"},
    )
    assert reuse.status_code == 422
    remote_ok = remote.post(
        "/v2/control/commands",
        params={"token": "founder"},
        json={"kind": "STOP", "reason": "auth-on", "command_id": "stop-auth"},
    )
    assert remote_ok.status_code == 200
    assert remote_ok.json()["applied"] is True
