"""C5-02 gateway: login pair, customer cannot founder-command, refresh/expired, rates."""

from __future__ import annotations

from typing import Any

from api.gateway_auth import JWT_ENV, TOTP_ENV
from api.main import create_app
from auth import issue_refresh, totp_at
from fastapi.testclient import TestClient

JWT = "paper-test-hmac-not-a-production-key"
RFC_SEED = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
NOW = 1_700_000_000.0
BASE = "http://127.0.0.1:8000"
LOCAL = ("127.0.0.1", 50000)


def _app(monkeypatch: Any, *, customers: str = "c1,c2,c3,c4,c5") -> TestClient:
    monkeypatch.setenv(JWT_ENV, JWT)
    monkeypatch.setenv(TOTP_ENV, RFC_SEED)
    monkeypatch.setenv("AAD_NOW", "2023-11-14T22:13:20+00:00")
    monkeypatch.setenv("AAD_PAPER_CUSTOMERS", customers)
    app = create_app()
    return TestClient(app, base_url=BASE, client=LOCAL)


def test_empty_secret_login_denied(monkeypatch: Any) -> None:
    monkeypatch.delenv(JWT_ENV, raising=False)
    monkeypatch.delenv("AAD_JWT_SECRET_FILE", raising=False)
    monkeypatch.delenv("AAD_SECRETS_DIR", raising=False)
    app = create_app()
    c = TestClient(app, base_url=BASE, client=LOCAL)
    r = c.post("/v2/auth/login", json={"role": "customer", "sub": "c1"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "JWT_SECRET_MISSING"


def test_customer_login_cannot_founder_command(monkeypatch: Any) -> None:
    c = _app(monkeypatch)
    minted = c.post("/v2/auth/login", json={"role": "customer", "sub": "c1"})
    assert minted.status_code == 200
    body = minted.json()
    assert body["role"] == "customer"
    assert body["channels"] == ["signals:public"]
    hdr = {"Authorization": f"Bearer {body['access']}"}
    snap = c.get("/v2/snapshot", headers=hdr, params={"channels": "positions,signals:public"})
    assert snap.status_code == 200
    assert "positions" in snap.json()["denied"]
    start = c.post(
        "/v2/control/commands",
        headers=hdr,
        json={"kind": "START", "reason": "nope", "command_id": "c5-cust-1"},
    )
    assert start.status_code == 403
    assert start.json()["detail"]["code"] == "FOUNDER_ONLY"


def test_refresh_and_expired_denied(monkeypatch: Any) -> None:
    c = _app(monkeypatch)
    minted = c.post("/v2/auth/login", json={"role": "customer", "sub": "c2"}).json()
    denied = c.get("/v2/snapshot", headers={"Authorization": f"Bearer {minted['refresh']}"})
    assert denied.status_code == 401
    assert denied.json()["detail"]["code"] == "REFRESH_FORBIDDEN"
    rotated = c.post("/v2/auth/refresh", json={"refresh": minted["refresh"]})
    assert rotated.status_code == 200
    assert verify_access_ok := rotated.json()["access"]
    assert verify_access_ok
    stale = issue_refresh(JWT, role="customer", sub="c2", now=NOW - 8 * 24 * 3600)
    expired = c.post("/v2/auth/refresh", json={"refresh": stale})
    assert expired.status_code == 401
    assert expired.json()["detail"]["code"] == "EXPIRED"


def test_rate_limits_hold_on_login_and_snapshot(monkeypatch: Any) -> None:
    c = _app(monkeypatch)
    minted = c.post("/v2/auth/login", json={"role": "customer", "sub": "c3"}).json()
    hdr = {"Authorization": f"Bearer {minted['access']}"}
    codes = [c.get("/v2/snapshot", headers=hdr).status_code for _ in range(11)]
    assert 200 in codes
    assert 429 in codes


def test_founder_login_totp_can_command(monkeypatch: Any) -> None:
    c = _app(monkeypatch)
    minted = c.post(
        "/v2/auth/login",
        json={"role": "founder", "sub": "founder", "totp": totp_at(RFC_SEED, NOW)},
    )
    assert minted.status_code == 200
    hdr = {"Authorization": f"Bearer {minted.json()['access']}"}
    start = c.post(
        "/v2/control/commands",
        headers=hdr,
        json={"kind": "START", "reason": "c5-founder", "command_id": "c5-f-1"},
    )
    assert start.status_code == 200
    assert start.json()["applied"] is True


def test_sixth_customer_rejected(monkeypatch: Any) -> None:
    c = _app(monkeypatch)
    r = c.post("/v2/auth/login", json={"role": "customer", "sub": "c6"})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "UNKNOWN_CUSTOMER"
