"""Standing pause/kill/lots cap live in the desk state dir and survive create_app restart."""

from __future__ import annotations

from api.main import create_app
from fastapi.testclient import TestClient

LOCAL = ("127.0.0.1", 12345)
BASE = "http://127.0.0.1"


def test_v2_11_control_state_survives_api_restart(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AAD_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("AAD_NOW", "2026-09-28T10:01:00+05:30")
    first = TestClient(create_app(), client=LOCAL, base_url=BASE)
    pause = first.post(
        "/v2/control/commands",
        json={"kind": "PAUSE", "args": {"minutes": 30}, "reason": "persist", "command_id": "persist-pause"},
    )
    assert pause.status_code == 200
    assert pause.json()["status"] == "applied"
    lots = first.post(
        "/v2/control/commands",
        json={"kind": "SET_LOTS", "args": {"lots": 1}, "reason": "persist", "command_id": "persist-lots"},
    )
    assert lots.json()["status"] == "applied"
    assert (tmp_path / "data" / "ledger" / "founder_controls.jsonl").is_file()

    second = TestClient(create_app(), client=LOCAL, base_url=BASE)
    state = second.get("/v2/control").json()["state"]
    assert state["paused_until_ist"]
    assert state["lots"] == 1
    resent = second.post(
        "/v2/control/commands",
        json={"kind": "PAUSE", "args": {"minutes": 30}, "reason": "persist", "command_id": "persist-pause"},
    )
    assert resent.status_code == 200
    body = resent.json()
    assert body["status"] == "applied"
    assert body["command_id"] == "persist-pause"
