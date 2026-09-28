"""V2 gateway auth: unauth rejected, bad host, WS auth, mutating control rate limit, legacy unchanged."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
from api.gateway_auth import (
    BIND_ENV,
    TOKEN_ENV,
    TOKEN_FILE_ENV,
    CommandRateLimiter,
    assert_bind_allowed,
    bind_host_from_argv,
    check_host_origin,
    effective_bind_host,
    identity_from_headers,
    load_gateway_auth,
    parse_host_header,
    parse_origin,
    query_has_auth_attempt,
    tokens_match,
)
from api.main import create_app
from api.v2_gateway import MUTATING_CONTROL_METHODS, GatewayHub, _rate_limit_command
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketDenialResponse
from starlette.websockets import WebSocketDisconnect

FOUNDER = "gw-test-founder"
CUSTOMER = "gw-test-customer"
BASE = "http://127.0.0.1:8000"
LOCAL = ("127.0.0.1", 50000)


def _app() -> tuple[TestClient, GatewayHub]:
    app = create_app()
    return TestClient(app, base_url=BASE, client=LOCAL), app.state.v2_hub


def _ws(client: TestClient, path: str, **kwargs: Any) -> Any:
    headers = dict(kwargs.pop("headers", None) or {})
    headers.setdefault("Host", "127.0.0.1:8000")
    return client.websocket_connect(path, headers=headers, **kwargs)


def test_unauth_rejected(monkeypatch: Any) -> None:
    monkeypatch.setenv(TOKEN_ENV, FOUNDER)
    monkeypatch.setenv("AAD_GATEWAY_CUSTOMER_TOKEN", CUSTOMER)
    c, _hub = _app()
    missing = c.get("/v2/snapshot")
    assert missing.status_code == 401
    assert missing.json()["detail"]["code"] == "UNAUTHORIZED"
    bad = c.get("/v2/snapshot", headers={"Authorization": "Bearer not-the-token"})
    assert bad.status_code == 401
    query = c.get("/v2/snapshot", params={"token": FOUNDER})
    assert query.status_code == 401
    sneak = c.get("/v2/snapshot", params={"access_token": FOUNDER})
    assert sneak.status_code == 401
    assert sneak.json()["detail"]["code"] == "QUERY_TOKEN_REFUSED"
    founder = c.get("/v2/snapshot", headers={"Authorization": f"Bearer {FOUNDER}"})
    assert founder.status_code == 200
    assert founder.json()["role"] == "founder"
    customer = c.get(
        "/v2/snapshot",
        headers={"Authorization": f"Bearer {CUSTOMER}"},
        params={"token": "founder", "channels": "positions"},
    )
    assert customer.status_code == 200
    assert customer.json()["role"] == "customer"
    assert "positions" in customer.json()["denied"]
    control = c.post("/v2/control/commands", json={"kind": "KILL", "reason": "x"})
    assert control.status_code == 401


def test_bad_host_rejected() -> None:
    assert parse_host_header("127.0.0.1:8000") == parse_host_header("127.0.0.1:8000")
    assert parse_host_header("127.0.0.1:8000") is not None
    assert parse_host_header("127.0.0.1:8000").host == "127.0.0.1"  # type: ignore[union-attr]
    assert parse_host_header("127.0.0.1:8000").port == 8000  # type: ignore[union-attr]
    assert parse_host_header("127.0.0.1:8000.evil.com") is None
    assert parse_host_header("127.0.0.1:80@evil") is None
    assert parse_host_header("[::1]:8000") is not None
    lookalike = parse_host_header("127.0.0.1.evil.example")
    assert lookalike is not None and lookalike.host == "127.0.0.1.evil.example"
    settings = load_gateway_auth()
    assert check_host_origin("127.0.0.1.evil.example", None, settings) == "bad_host"
    assert check_host_origin("127.0.0.1:8000.evil.com", None, settings) == "bad_host"
    assert parse_origin("http://127.0.0.1.evil.com:5173") is not None
    assert (
        check_host_origin("127.0.0.1:8000", "http://127.0.0.1.evil.com:5173", settings)
        == "bad_origin"
    )
    c, _hub = _app()
    for host in (
        "evil.example",
        "evil.example:8000",
        "127.0.0.1.evil.example",
        "127.0.0.1:8000.evil.com",
        "",
    ):
        r = c.get("/v2/snapshot", headers={"Host": host})
        assert r.status_code == 403, host
        assert r.json()["detail"]["code"] == "BAD_HOST"
    assert c.get("/v2/snapshot", headers={"Host": "127.0.0.1:8000"}).status_code == 200
    bad_origin = c.get(
        "/v2/snapshot",
        headers={"Host": "127.0.0.1:8000", "Origin": "http://127.0.0.1.evil.com:5173"},
    )
    assert bad_origin.status_code == 403
    assert bad_origin.json()["detail"]["code"] == "BAD_ORIGIN"
    ok_origin = c.get(
        "/v2/snapshot",
        headers={"Host": "127.0.0.1:8000", "Origin": "http://127.0.0.1:5173"},
    )
    assert ok_origin.status_code == 200
    with (
        pytest.raises(WebSocketDenialResponse),
        _ws(c, "/v2/ws", headers={"Host": "127.0.0.1:8000.evil.com"}),
    ):
        pass


def test_ws_auth(monkeypatch: Any) -> None:
    monkeypatch.setenv(TOKEN_ENV, FOUNDER)
    c, _hub = _app()

    with _ws(c, "/v2/ws") as ws:
        ws.send_json({"op": "subscribe", "channels": ["positions"]})
        denied = ws.receive_json()
        assert denied.get("code") == "UNAUTHORIZED"
        with pytest.raises(WebSocketDisconnect) as missing:
            ws.receive_json()
    assert missing.value.code == 4401

    with (
        pytest.raises(WebSocketDenialResponse),
        _ws(c, f"/v2/ws?access_token={FOUNDER}") as ws,
    ):
        ws.receive_json()

    with _ws(c, "/v2/ws") as ws:
        ws.send_json(
            {
                "token": FOUNDER,
                "op": "subscribe",
                "channels": ["positions"],
            }
        )
        snap = ws.receive_json()
        assert snap["op"] == "snapshot"
        assert snap["channel"] == "positions"

    with _ws(c, "/v2/ws", subprotocols=[f"bearer.{FOUNDER}"]) as ws:
        ws.send_json({"op": "subscribe", "channels": ["positions"]})
        assert ws.receive_json()["op"] == "snapshot"

    with _ws(c, "/v2/ws", headers={"Authorization": f"Bearer {FOUNDER}"}) as ws:
        ws.send_json({"op": "subscribe", "channels": ["positions"]})
        assert ws.receive_json()["op"] == "snapshot"

    with _ws(c, "/v2/ws") as ws:
        ws.send_json({"token": "nope", "op": "subscribe", "channels": ["positions"]})
        msg = ws.receive_json()
        assert msg.get("code") == "UNAUTHORIZED"
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


def test_mutating_control_commands_are_rate_limited(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Mutating control commands are rate-limited (1/s). GET is intentionally not."""
    from fastapi import HTTPException
    from starlette.requests import Request

    caplog.set_level(logging.INFO, logger="api.v2.control")
    c, _hub = _app()
    assert MUTATING_CONTROL_METHODS == frozenset({"POST", "PUT", "PATCH", "DELETE"})
    for _ in range(3):
        surface = c.get("/v2/control")
        assert surface.status_code == 200
        assert surface.json()["stub"] is False
    first = c.post("/v2/control/commands", json={"kind": "KILL", "reason": "x"})
    assert first.status_code == 422
    second = c.post("/v2/control/commands", json={"kind": "START", "reason": "go"})
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "RATE_LIMIT"
    after = c.get("/v2/control")
    assert after.status_code == 200
    assert after.json()["stub"] is False

    def _req(method: str) -> Request:
        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        return Request(
            {
                "type": "http",
                "asgi": {"spec_version": "2.3", "version": "3.0"},
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": "/v2/control/commands",
                "raw_path": b"/v2/control/commands",
                "query_string": b"",
                "headers": [(b"host", b"127.0.0.1:8000")],
                "client": LOCAL,
                "server": ("127.0.0.1", 8000),
                "app": c.app,
            },
            receive,
        )

    for method in MUTATING_CONTROL_METHODS - {"POST"}:
        with pytest.raises(HTTPException) as exc:
            _rate_limit_command(_req(method))
        assert exc.value.status_code == 429
        assert exc.value.detail["code"] == "RATE_LIMIT"

    text = caplog.text
    assert "control_command" in text
    assert "confirm_required" in text
    assert "rate_limited" in text
    assert "KILL" in text
    assert FOUNDER not in text
    assert "Bearer" not in text


def test_legacy_endpoints_unchanged(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setenv(TOKEN_ENV, FOUNDER)
    app = create_app()
    app.state.founder_root = tmp_path
    c = TestClient(app, client=LOCAL, base_url=BASE)
    assert c.get("/health").status_code == 200
    assert c.get("/paper/signal").status_code == 200
    assert c.get("/paper/live-signals").status_code == 200
    assert c.get("/paper/history").status_code == 200
    assert c.get("/founder/status").status_code == 200
    assert c.get("/founder/controls").status_code == 200
    assert c.get("/ui/snapshot").status_code == 200
    # V2 still requires the bearer when a token is configured
    assert c.get("/v2/snapshot").status_code == 401


def test_localhost_dev_needs_no_token() -> None:
    c, _hub = _app()
    assert c.get("/v2/snapshot").status_code == 200
    assert c.get("/v2/snapshot").json()["role"] == "customer"
    with _ws(c, "/v2/ws?token=founder") as ws:
        ws.send_json({"op": "subscribe", "channels": ["positions"]})
        assert ws.receive_json()["op"] == "snapshot"


def test_bind_refuses_public_without_token() -> None:
    with pytest.raises(ValueError, match="refusing bind"):
        assert_bind_allowed("0.0.0.0", False)
    with pytest.raises(ValueError, match="refusing bind"):
        assert_bind_allowed("::", False)
    assert_bind_allowed("127.0.0.1", False)
    assert_bind_allowed("0.0.0.0", True)


def test_bind_env_refuses_create_app(monkeypatch: Any) -> None:
    monkeypatch.setenv(BIND_ENV, "0.0.0.0")
    monkeypatch.delenv(TOKEN_ENV, raising=False)
    monkeypatch.delenv(TOKEN_FILE_ENV, raising=False)
    with pytest.raises(ValueError, match="refusing bind"):
        create_app()
    monkeypatch.setenv(TOKEN_ENV, FOUNDER)
    app = create_app()
    assert app.state.v2_auth.configured is True


def test_uvicorn_cli_host_refuses_public_without_token(monkeypatch: Any) -> None:
    """``uvicorn --host 0.0.0.0`` fails closed unless a gateway token is set."""
    monkeypatch.delenv(TOKEN_ENV, raising=False)
    monkeypatch.delenv(TOKEN_FILE_ENV, raising=False)
    monkeypatch.delenv(BIND_ENV, raising=False)
    assert bind_host_from_argv(["uvicorn", "api.main:app", "--host", "0.0.0.0"]) == (
        "0.0.0.0"
    )
    assert bind_host_from_argv(["uvicorn", "api.main:app", "--host=::"]) == "::"
    assert bind_host_from_argv(["pytest", "apps/api/tests"]) is None
    assert effective_bind_host("127.0.0.1", ["uvicorn", "--host", "0.0.0.0"]) == (
        "0.0.0.0"
    )
    monkeypatch.setattr(
        "api.gateway_auth.bind_host_from_argv", lambda argv=None: "0.0.0.0"
    )
    with pytest.raises(ValueError, match="refusing bind"):
        create_app()


def test_token_file_and_constant_time(tmp_path: Path, monkeypatch: Any) -> None:
    path = tmp_path / "gateway_token"
    path.write_text(f"{FOUNDER}\n", encoding="utf-8")
    monkeypatch.setenv(TOKEN_FILE_ENV, str(path))
    monkeypatch.delenv(TOKEN_ENV, raising=False)
    settings = load_gateway_auth()
    assert settings.configured is True
    assert tokens_match(FOUNDER, settings.founder_token) is True
    assert tokens_match("nope", settings.founder_token) is False
    assert tokens_match("", settings.founder_token) is False
    assert identity_from_headers(f"Bearer {FOUNDER}", None, settings) is not None
    assert identity_from_headers(None, f"bearer.{FOUNDER}", settings).role == "founder"  # type: ignore[union-attr]
    assert query_has_auth_attempt("token=founder") is False
    assert query_has_auth_attempt("access_token=x") is True


def test_rate_limiter_one_per_second() -> None:
    ticks = iter([0.0, 0.1, 1.1])
    lim = CommandRateLimiter(per_s=1.0, clock=lambda: next(ticks))
    assert lim.allow("ip") is True
    assert lim.allow("ip") is False
    assert lim.allow("ip") is True
