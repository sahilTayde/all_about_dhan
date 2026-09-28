"""Founder emergency control routes: validation, confirmation tokens, localhost-only, ack + history."""

import json
import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import founder_controls as fcr
from api.main import create_app
from desk_ml.founder_commands import append_statuses, make_row, read_commands
from desk_ml.founder_commands.log import first_seen_path

REPO = Path(__file__).resolve().parents[3]
LOCAL = ("127.0.0.1", 50000)
BASE = "http://127.0.0.1:8000"


@pytest.fixture
def root(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    shutil.copy(REPO / "config" / "risk_limits.yaml", tmp_path / "config" / "risk_limits.yaml")
    monkeypatch.setenv("AAD_FOUNDER_SPOOL_DIR", str(tmp_path / "spool"))
    monkeypatch.delenv(fcr.REMOTE_ENV, raising=False)
    return tmp_path


@pytest.fixture
def client(root):
    app = create_app()
    app.state.founder_root = root
    return TestClient(app, client=LOCAL, base_url=BASE)


def token(client, kind, trade_id=None):
    r = client.post("/founder/controls/confirm", json={"kind": kind, "trade_id": trade_id})
    assert r.status_code == 200, r.text
    return r.json()["confirm_token"]


ROUTES = [
    ("start", "START", {}),
    ("stop", "STOP", {}),
    ("pause", "PAUSE", {"minutes": 15}),
    ("blocked-windows", "BLOCK_WINDOWS", {"windows": [{"start": "09:15", "end": "09:30"}, {"start": "14:45", "end": "15:30"}]}),
    ("go-t2", "GO_T2", {"trade_id": "paper-MIX-DEFAULT-BUY-NIFTY-1-CE"}),
    ("lots", "SET_LOTS", {"lots": 20}),
    ("index", "INDEX", {"underlying": "FINNIFTY", "enabled": False}),
    ("min-capital", "MIN_CAPITAL", {"amount_inr": 300000}),
    ("add-funds", "ADD_FUNDS", {"amount_inr": 50000}),
]


def test_localhost_only(root, monkeypatch):
    app = create_app()
    app.state.founder_root = root
    assert TestClient(app, base_url=BASE).get("/founder/controls").status_code == 403  # client "testclient"
    remote = TestClient(app, client=("10.0.0.7", 1), base_url=BASE)
    assert remote.post("/founder/controls/stop", json={"reason": "x"}).status_code == 403
    local = TestClient(app, client=LOCAL, base_url=BASE)
    assert local.get("/founder/controls").status_code == 200
    assert local.get("/founder/controls", headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 403
    for host in ("localhost:5173", "[::1]:8000", "127.0.0.1"):
        assert local.get("/founder/controls", headers={"Host": host}).status_code == 200, host
    for host in (
        "evil.example",
        "evil.example:8000",
        "127.0.0.1.evil.example",
        "127.0.0.1:8000.evil.com",
        "",
    ):  # DNS rebinding / look-alike Host
        assert local.post("/founder/controls/stop", json={"reason": "x"}, headers={"Host": host}).status_code == 403, host
    assert TestClient(app, client=LOCAL).get("/founder/controls").status_code == 403  # Host "testserver"
    monkeypatch.setenv(fcr.REMOTE_ENV, "1")
    assert remote.get("/founder/controls").status_code == 200
    assert read_commands(root).rows == []  # the refused POST wrote nothing


@pytest.mark.parametrize("path,kind,args", ROUTES)
def test_each_route_appends_one_timestamped_command(client, root, path, kind, args):
    r = client.post(f"/founder/controls/{path}", json={"reason": f"test {kind}", "actor": "sahil", **args})
    assert r.status_code == 200, r.text
    ack = r.json()
    assert ack["ack"] and ack["recorded"] and ack["status"] == "pending" and ack["kind"] == kind
    rows = read_commands(root).rows
    assert len(rows) == 1
    row = rows[0]
    assert (row["id"], row["kind"], row["actor"], row["reason"]) == (ack["id"], kind, "sahil", f"test {kind}")
    assert row["ts"] == ack["ts"] and row["session"] == ack["ts_ist"][:10]


def test_kill_needs_a_single_use_confirmation(client, root):
    assert client.post("/founder/controls/kill", json={"reason": "crash"}).status_code == 422
    bad = client.post("/founder/controls/kill", json={"reason": "crash", "confirm_token": "nope"})
    assert bad.status_code == 409 and bad.json()["detail"]["status_reason"].startswith("CONFIRMATION_REQUIRED")
    tok = token(client, "KILL")
    ok = client.post("/founder/controls/kill", json={"reason": "crash", "confirm_token": tok})
    assert ok.status_code == 200 and ok.json()["status"] == "pending"
    reuse = client.post("/founder/controls/kill", json={"reason": "again", "confirm_token": tok})
    assert reuse.status_code == 409 and "already used" in reuse.json()["detail"]["status_reason"]
    rearm = client.post("/founder/controls/rearm", json={"reason": "ok now", "confirm_token": token(client, "REARM")})
    assert rearm.status_code == 200
    kinds = [(r["kind"], r.get("status")) for r in read_commands(root).rows]
    assert kinds == [("KILL", "rejected"), ("KILL", None), ("KILL", "rejected"), ("REARM", None)]  # rejections are audited


def test_cut_loss_token_is_bound_to_the_trade(client, root):
    tok = token(client, "CUT_LOSS", "trade-A")
    wrong = client.post("/founder/controls/cut-loss", json={"reason": "r", "trade_id": "trade-B", "confirm_token": tok})
    assert wrong.status_code == 409
    right = client.post("/founder/controls/cut-loss", json={"reason": "r", "trade_id": "trade-A", "confirm_token": token(client, "CUT_LOSS", "trade-A")})
    assert right.status_code == 200 and right.json()["args"] == {"trade_id": "trade-A"}
    assert client.post("/founder/controls/confirm", json={"kind": "CUT_LOSS"}).status_code == 422


def test_resent_command_id_is_idempotent(client, root):
    body = {"reason": "stop", "command_id": "ui-123"}
    first = client.post("/founder/controls/stop", json=body).json()
    second = client.post("/founder/controls/stop", json=body).json()
    assert second["duplicate"] and second["id"] == first["id"] == "ui-123" and second["ts"] == first["ts"]
    assert len(read_commands(root).rows) == 1


def test_lots_must_stay_within_risk_limits(client, root):
    ok = client.post("/founder/controls/lots", json={"reason": "size", "lots": 25})
    assert ok.status_code == 200
    over = client.post("/founder/controls/lots", json={"reason": "size", "lots": 26})
    assert over.status_code == 409 and over.json()["detail"]["status_reason"].startswith("LOTS_OVER_LIMIT: at most 25")
    assert client.post("/founder/controls/lots", json={"reason": "clear", "lots": None}).status_code == 200
    (root / "config" / "risk_limits.yaml").write_text("mode: [broken", encoding="utf-8")
    broken = client.post("/founder/controls/lots", json={"reason": "size", "lots": 5})
    assert broken.status_code == 409 and broken.json()["detail"]["status_reason"].startswith("RISK_LIMITS_UNREADABLE")


@pytest.mark.parametrize("path,body", [
    ("pause", {"reason": "r", "minutes": -1}),
    ("pause", {"reason": "r", "minutes": 5, "surprise": 1}),
    ("stop", {}),
    ("stop", {"reason": ""}),
    ("blocked-windows", {"reason": "r", "windows": [{"start": "14:45", "end": "14:00"}]}),
    ("blocked-windows", {"reason": "r", "windows": [{"start": "9:15", "end": "09:30"}]}),
    ("index", {"reason": "r", "underlying": "nifty", "enabled": True}),
    ("add-funds", {"reason": "r", "amount_inr": 0}),
    ("lots", {"reason": "r", "lots": 0}),
    ("go-t2", {"reason": "r"}),
])
def test_validation(client, root, path, body):
    assert client.post(f"/founder/controls/{path}", json=body).status_code == 422
    assert read_commands(root).rows == []


def test_not_recorded_is_reported_loudly(client, root, monkeypatch):
    def full(*a, **k):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("desk_ml.founder_commands.append_command", full)
    r = client.post("/founder/controls/stop", json={"reason": "r"})
    assert r.status_code == 503 and r.json()["detail"]["recorded"] is False


def test_add_funds_updates_the_account_view(client, root):
    client.post("/founder/controls/add-funds", json={"reason": "top up", "amount_inr": 100000})
    client.post("/founder/controls/add-funds", json={"reason": "top up", "amount_inr": 25000.5})
    client.post("/founder/controls/min-capital", json={"reason": "floor", "amount_inr": 400000})
    view = json.loads((root / "data" / "recon" / "founder_account.json").read_text(encoding="utf-8"))
    assert view["funds_added_inr"] == 125000.5 and view["min_capital_inr"] == 400000


def test_history_shows_pending_applied_and_rejected(client, root):
    ids = [client.post(f"/founder/controls/{p}", json={"reason": "r", **a}).json()["id"] for p, _k, a in ROUTES[:3]]
    client.post("/founder/controls/lots", json={"reason": "too big", "lots": 99})
    board = {
        "as_of_ist": "2026-09-10T12:00:00+05:30",
        "open_trades": [{"trade_id": "t1", "underlying": "NIFTY", "side": "CE", "lots": 25, "entry": 100.0, "extra": 1}],
        "founder_controls": {"results": [{"id": ids[0], "status": "applied", "applied_ts": 1789020000}]},
    }
    (root / "data" / "recon" / "ml_paper_dashboard.json").write_text(json.dumps(board), encoding="utf-8")
    append_statuses(root, [{"id": ids[1], "kind": "STOP", "status": "rejected", "status_reason": "TEST"}])
    body = client.get("/founder/controls").json()
    by = {c["id"]: c for c in body["commands"]}
    assert by[ids[0]]["status"] == "applied" and by[ids[0]]["applied_ist"] == "2026-09-10T11:30:00+05:30"
    assert (by[ids[1]]["status"], by[ids[1]]["status_reason"]) == ("rejected", "TEST")
    assert by[ids[2]]["status"] == "pending"
    rejected = next(c for c in body["commands"] if c["kind"] == "SET_LOTS")
    assert rejected["status"] == "rejected" and "LOTS_OVER_LIMIT" in rejected["status_reason"]
    assert [c["ts"] for c in body["commands"]] == sorted((c["ts"] for c in body["commands"]), reverse=True)
    assert body["open_trades"][0]["trade_id"] == "t1" and "extra" not in body["open_trades"][0]
    assert body["state"]["paused_until_ist"] and body["state"]["running"] is False  # START, STOP, PAUSE 15
    assert body["state"]["entries_blocked_reason"] == "FOUNDER_STOPPED"
    assert body["limits"]["max_lots"] == 25 and body["paper_only"] and body["orders"] == "REFUSED"


def test_history_uses_the_first_seen_anchor(client, root):
    """Entries are blocked from when the live loop first saw the bad line, not from the last good one."""
    now = time.time()
    path = root / "data" / "recon" / "founder_controls.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    good = make_row("START", {}, actor="t", reason="t", ts=now - 7200, command_id="g1")
    path.write_text(json.dumps(good) + "\ngarbage\n", encoding="utf-8")
    assert client.get("/founder/controls").json()["state"]["entries_blocked_reason"] == "FOUNDER_CONTROLS_UNREADABLE"
    key = read_commands(root).anchors[0][0]
    first_seen_path(root).write_text(json.dumps({key: now + 3600}), encoding="utf-8")  # loop sees it in an hour
    assert client.get("/founder/controls").json()["state"]["entries_blocked_reason"] is None


def test_corrupt_log_shows_entries_blocked(client, root):
    path = root / "data" / "recon" / "founder_controls.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("garbage\n", encoding="utf-8")
    body = client.get("/founder/controls").json()
    assert body["problems"] == ["log line 1: not JSON"]
    assert body["state"]["entries_blocked_reason"] == "FOUNDER_CONTROLS_UNREADABLE"
