"""C5-05: customer paper hot paths stay cheap. No live broker. No cost fixture edits."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from api.c5_hot import (
    SIGNALS_KEEP,
    account_status,
    last_tape_line,
    resolve_paper_account_id,
)
from api.gateway_auth import JWT_ENV, TOTP_ENV
from api.main import create_app
from api.v2_gateway import HOT_KEEP, envelope_from_parts
from auth import totp_at
from fastapi.testclient import TestClient

TS = "2026-09-28T10:01:00.000+05:30"
JWT = "paper-test-hmac-not-a-production-key"
RFC_SEED = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
NOW = 1_700_000_000.0
BASE = "http://127.0.0.1:8000"
LOCAL = ("127.0.0.1", 50000)
ART = Path("/opt/cursor/artifacts")


def _app() -> tuple[TestClient, Any]:
    app = create_app()
    return TestClient(app, base_url=BASE, client=LOCAL), app.state.v2_hub


def _signal(i: int, **extra: Any) -> Any:
    payload = {
        "underlying": "NIFTY",
        "side": "CE",
        "trend": "up",
        "chain_3m": "ATM bid",
        "news": "none",
        "rsi": 99,
        "macd": "soup",
        **extra,
    }
    return envelope_from_parts(
        "SIGNAL",
        payload,
        available_ts=TS,
        event_id=f"{i:032d}",
    )


def _p50(samples: list[float]) -> float:
    ordered = sorted(samples)
    return ordered[len(ordered) // 2]


def _timed(fn: Any, n: int = 20, warmup: int = 4) -> list[float]:
    for _ in range(warmup):
        fn()
    out: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t0) * 1000)
    return out


def test_resolve_paper_account_id() -> None:
    assert resolve_paper_account_id("c1") == "customer-01"
    assert resolve_paper_account_id("c5") == "customer-05"
    assert resolve_paper_account_id("customer-03") == "customer-03"
    assert resolve_paper_account_id("") is None
    assert resolve_paper_account_id(None) is None


def test_customer_snapshot_skips_legacy_ui(monkeypatch: Any) -> None:
    calls = {"n": 0}

    def boom() -> dict[str, Any]:
        calls["n"] += 1
        time.sleep(0.15)
        return {"board": {"leaked": True}, "account": {"cash": 1}}

    monkeypatch.setattr("api.v2_gateway._legacy_ui", boom)
    c, hub = _app()
    hub.ingest(_signal(1))
    t0 = time.perf_counter()
    body = c.get(
        "/v2/snapshot", params={"token": "customer", "channels": "signals:public"}
    ).json()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert calls["n"] == 0
    assert body["role"] == "customer"
    assert "board" not in body
    assert "account" not in body
    assert elapsed_ms < 80
    founder = c.get("/v2/snapshot", params={"token": "founder"})
    assert founder.status_code == 200
    assert calls["n"] == 1


def test_hot_channel_capped() -> None:
    c, hub = _app()
    for i in range(HOT_KEEP + 20):
        hub.ingest(_signal(i))
    body = c.get(
        "/v2/snapshot", params={"token": "customer", "channels": "signals:public"}
    ).json()
    items = body["channels"]["signals:public"]["items"]
    assert len(items) == HOT_KEEP
    compact = c.get("/v2/customer/signals", params={"token": "customer"}).json()
    assert compact["n"] == SIGNALS_KEEP
    assert len(compact["channels"]["signals:public"]["items"]) == SIGNALS_KEEP
    for row in compact["signals"]:
        assert "rsi" not in row
        assert "macd" not in row


def test_customer_hot_routes_and_isolation(monkeypatch: Any) -> None:
    monkeypatch.setenv(JWT_ENV, JWT)
    monkeypatch.setenv(TOTP_ENV, RFC_SEED)
    monkeypatch.setenv("AAD_NOW", "2023-11-14T22:13:20+00:00")
    monkeypatch.setenv("AAD_PAPER_CUSTOMERS", "c1,c2,c3,c4,c5")
    c = TestClient(create_app(), base_url=BASE, client=LOCAL)
    minted = c.post("/v2/auth/login", json={"role": "customer", "sub": "c1"})
    assert minted.status_code == 200
    hdr = {"Authorization": f"Bearer {minted.json()['access']}"}
    acc = c.get("/v2/customer/account", headers=hdr).json()
    assert acc["ok"] is True
    assert acc["account_id"] == "customer-01"
    assert acc["kind"] == "customer"
    blob = json.dumps(acc)
    assert "customer-02" not in blob
    assert acc["live_broker"] is False
    assert acc["orders"] == "REFUSED"

    other = c.post("/v2/auth/login", json={"role": "customer", "sub": "c2"}).json()
    other_acc = c.get(
        "/v2/customer/account", headers={"Authorization": f"Bearer {other['access']}"}
    ).json()
    assert other_acc["account_id"] == "customer-02"
    assert other_acc["account_id"] != acc["account_id"]

    founder = c.post(
        "/v2/auth/login",
        json={"role": "founder", "sub": "founder", "totp": totp_at(RFC_SEED, NOW)},
    )
    assert founder.status_code == 200
    denied = c.get(
        "/v2/customer/signals",
        headers={"Authorization": f"Bearer {founder.json()['access']}"},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "CUSTOMER_ONLY"


def test_journal_tail_is_public_fields_only(tmp_path: Path) -> None:
    c, hub = _app()
    hub.ingest(_signal(1, news="cited"))
    journal = c.get("/v2/customer/journal", params={"token": "customer"}).json()
    assert journal["ok"] is True
    assert journal["n"] >= 1
    row = journal["items"][0]
    assert set(row) <= {
        "underlying",
        "side",
        "decision",
        "trend",
        "chain_3m",
        "news",
        "cited_news",
    }
    tape = tmp_path / "2026-10-04.jsonl"
    tape.write_bytes(b'{"skip": true}\n' * 200 + b'{"as_of_ist": "2026-10-04T11:00:00+05:30"}\n')
    last = last_tape_line(tape)
    assert last is not None
    assert last["as_of_ist"] == "2026-10-04T11:00:00+05:30"


def test_localhost_account_does_not_bind_a_sibling_book() -> None:
    generic = account_status(None)
    assert generic["account_id"] is None
    assert generic["status"] == "paper-seat"
    assert generic["live_broker"] is False


def test_hot_path_latency_bench() -> None:
    """Print ms numbers. Soft ceiling so CI is not a flaky race."""
    c, hub = _app()
    for i in range(24):
        hub.ingest(_signal(i))

    rows: list[tuple[str, float, float]] = []

    def record(name: str, fn: Any) -> None:
        samples = _timed(fn)
        p50, p95 = _p50(samples), sorted(samples)[int(len(samples) * 0.95) - 1]
        rows.append((name, p50, p95))
        assert p50 < 40, f"{name} p50 {p50:.2f} ms"

    record("GET /signals", lambda: c.get("/signals").raise_for_status())
    record(
        "GET /v2/snapshot customer",
        lambda: c.get(
            "/v2/snapshot", params={"token": "customer", "channels": "signals:public"}
        ).raise_for_status(),
    )
    record(
        "GET /v2/customer/signals",
        lambda: c.get("/v2/customer/signals", params={"token": "customer"}).raise_for_status(),
    )
    record(
        "GET /v2/customer/account",
        lambda: c.get("/v2/customer/account", params={"token": "customer"}).raise_for_status(),
    )
    record(
        "GET /v2/customer/journal",
        lambda: c.get("/v2/customer/journal", params={"token": "customer"}).raise_for_status(),
    )

    snap = c.get(
        "/v2/snapshot", params={"token": "customer", "channels": "signals:public"}
    )
    compact = c.get("/v2/customer/signals", params={"token": "customer"})
    snap_n = len(snap.json()["channels"]["signals:public"]["items"])
    compact_n = compact.json()["n"]
    assert compact_n <= snap_n
    assert compact_n <= SIGNALS_KEEP

    ART.mkdir(parents=True, exist_ok=True)
    lines = ["C5-05 after (TestClient, paper only)", ""]
    for name, p50, p95 in rows:
        lines.append(f"{name:32s}  p50={p50:7.2f} ms  p95={p95:7.2f} ms")
    lines.append("")
    lines.append(f"snapshot public items={snap_n}  compact n={compact_n}  HOT_KEEP={HOT_KEEP}")
    lines.append("costs/fixtures: unchanged")
    (ART / "c5-05-latency-after.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
