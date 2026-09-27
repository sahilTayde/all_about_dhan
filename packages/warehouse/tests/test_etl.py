"""Nightly ETL: idempotent, incremental, read-only helpers. Synthetic rows only (not market data)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from warehouse import queries
from warehouse.etl import main as etl_main
from warehouse.etl import run_etl

REPO = Path(__file__).resolve().parents[3]
D1, D2 = "2026-09-07", "2026-09-08"  # Monday, Tuesday
T0 = 1788753600  # 2026-09-07 09:30 IST


def _trade(tid: str, net: float, *, day_offset: int = 0, reason: str = "TARGET", book: str = "MIX-DEFAULT-BUY",
           filled: bool = True, **extra) -> dict:
    ts = T0 + day_offset * 86400
    return {"trade_id": tid, "book_id": book, "underlying": "NIFTY", "side": "CE", "atm_strike": 25000.0,
            "opened_ts": ts, "closed_ts": ts + 300, "entry": 200.0, "exit": 200.0 + net / 65, "limit_price": 199.5,
            "qty": 65, "lots": 1, "exit_reason": reason, "gross_pnl_inr": net + 50, "charges_inr": 50.0,
            "realized_pnl_inr": net, "filled": filled, **extra}


def _write_jsonl(path: Path, rows: list[dict], mode: str = "w") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(mode, encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    recon = tmp_path / "data" / "recon"
    _write_jsonl(recon / "paper_booked" / f"{D1}.jsonl", [_trade("t1", 1000.0), _trade("t2", -400.0, reason="STOP")])
    (recon / "paper_booked" / f"{D1}.state.json").write_text("{}", encoding="utf-8")
    board = {"session_ist_date": D2, "skip_reason_counts": {"HOLD_MAJORITY": 7, "SOD_ONE_OPEN": 3},
             "closed_trades": [
                 _trade("t3", 250.0, day_offset=1, model_names=["STRAT-003", "MIX-TV-EP-024"], brokerage_inr=40.0),
                 _trade("t4", -90.0, day_offset=1, reason="CANCEL_STALL", model_names=["STRAT-003"]),
                 _trade("t5", 0.0, day_offset=1, filled=False),
             ]}
    (recon / "ml_paper_dashboard.json").write_text(json.dumps(board), encoding="utf-8")
    _write_jsonl(recon / "ml_paper_model_logs.jsonl", [
        {"event": "OPEN", "book_id": "MIX-DEFAULT-BUY", "trade_id": "t1", "status": "OPEN", "ts": T0},
        {"event": "CLOSE", "book_id": "MIX-DEFAULT-BUY", "trade_id": "t1", "status": "TARGET", "ts": T0 + 300},
    ])
    (recon / f"EOD_RECON_{D1}.json").write_text(json.dumps({"ok": True, "as_of_ist": f"{D1}T16:00:00+05:30",
                                                             "signal_count": 2, "nested": {"x": 1}}), encoding="utf-8")
    return tmp_path


def _db(root: Path) -> Path:
    return root / "data" / "warehouse" / "analytics.sqlite"


def test_loads_every_source_and_rollups(root: Path) -> None:
    out = run_etl(root=root)
    assert out["ok"], out["errors"]
    assert out["files_seen"] == 4  # booked jsonl, board, model log, EOD recon (state.json skipped)
    db = _db(root)
    daily = {(r["period"], r["book_id"]): r for r in queries.pnl(db, period="day")}
    assert daily[(D1, "MIX-DEFAULT-BUY")]["n_trades"] == 2
    assert daily[(D1, "MIX-DEFAULT-BUY")]["net_pnl"] == 600.0
    assert daily[(D1, "MIX-DEFAULT-BUY")]["win_rate_pct"] == 50.0
    assert daily[(D2, "MIX-DEFAULT-BUY")]["n_trades"] == 2  # unfilled t5 is not a trade
    weekly = queries.pnl(db, period="week")
    assert len(weekly) == 1 and weekly[0]["period"] == D1 and weekly[0]["n_trades"] == 4
    assert queries.pnl(db, period="month")[0]["period"] == "2026-09"
    models = {r["model"]: r for r in queries.model_attribution(db)}
    assert models["STRAT-003"]["n_trades"] == 2 and models["STRAT-003"]["net_pnl"] == 160.0
    assert models["MIX-TV-EP-024"]["n_trades"] == 1
    stages = {(r["stage"], r["outcome"], r["reason"]): r for r in queries.stage_attribution(db)}
    assert stages[("boss", "NO_ENTRY", "HOLD_MAJORITY")]["n"] == 7
    assert stages[("exit", "LOSS", "STOP")]["net_pnl"] == -400.0
    reasons = {r["exit_reason"] for r in queries.exit_reasons(db)}
    assert reasons == {"TARGET", "STOP", "CANCEL_STALL"}
    assert queries.slippage(db, since=D1, until=D1)[0]["avg_entry_slippage"] == 0.5
    assert queries.charges(db)[0]["charges"] == 100.0  # D2 first (newest), two filled trades × ₹50
    st = queries.etl_status(db)
    assert st["counts"]["model_log"] == 2 and st["counts"]["recon_reports"] == 1
    assert st["trade_days"] == {"first": D1, "last": D2}


def test_rerun_is_idempotent(root: Path) -> None:
    run_etl(root=root)
    before = queries.etl_status(_db(root))["counts"]
    again = run_etl(root=root)
    assert again["files_skipped"] == again["files_seen"] and again["rows"] == 0
    assert queries.etl_status(_db(root))["counts"] == before
    full = run_etl(root=root, full=True)
    assert full["files_loaded"] == full["files_seen"]
    assert queries.etl_status(_db(root))["counts"] == before


def test_appended_lines_are_tail_loaded(root: Path) -> None:
    run_etl(root=root)
    booked = root / "data" / "recon" / "paper_booked" / f"{D1}.jsonl"
    _write_jsonl(booked, [_trade("t6", 300.0)], mode="a")
    with booked.open("a", encoding="utf-8") as fh:
        fh.write('{"trade_id": "half-writ')  # writer mid-line: must wait for the next run
    out = run_etl(root=root)
    assert out["files_tailed"] == 1 and out["rows"] == 1
    assert queries.pnl(_db(root), since=D1, until=D1)[0]["n_trades"] == 3


def test_rewritten_file_is_replaced_not_duplicated(root: Path) -> None:
    run_etl(root=root)
    booked = root / "data" / "recon" / "paper_booked" / f"{D1}.jsonl"
    _write_jsonl(booked, [_trade("t1", 50.0)])  # shorter + different prefix = rewrite
    out = run_etl(root=root)
    assert out["files_loaded"] == 1
    row = queries.pnl(_db(root), since=D1, until=D1)[0]
    assert row["n_trades"] == 1 and row["net_pnl"] == 50.0


def test_board_keeps_earlier_session_days(root: Path) -> None:
    run_etl(root=root)
    board_path = root / "data" / "recon" / "ml_paper_dashboard.json"
    board_path.write_text(json.dumps({"session_ist_date": "2026-09-09",
                                      "closed_trades": [_trade("t9", 10.0, day_offset=2)]}), encoding="utf-8")
    run_etl(root=root)
    days = {r["period"] for r in queries.pnl(_db(root))}
    assert days == {D1, D2, "2026-09-09"}


def test_same_trade_in_two_sources_counts_once(root: Path) -> None:
    board_path = root / "data" / "recon" / "ml_paper_dashboard.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["closed_trades"].append(_trade("t1", 999.0))  # also in paper_booked (priority wins)
    board_path.write_text(json.dumps(board), encoding="utf-8")
    run_etl(root=root)
    row = queries.pnl(_db(root), since=D1, until=D1)[0]
    assert row["n_trades"] == 2 and row["net_pnl"] == 600.0


def test_bad_file_is_reported_and_others_still_load(root: Path) -> None:
    (root / "data" / "recon" / f"EOD_RECON_{D2}.json").write_text("{not json", encoding="utf-8")
    out = run_etl(root=root)
    assert not out["ok"] and len(out["errors"]) == 1
    assert queries.etl_status(_db(root))["counts"]["trades"] == 5  # includes the unfilled t5 row


def test_helpers_are_read_only_and_missing_db_is_empty(root: Path, tmp_path: Path) -> None:
    assert queries.pnl(tmp_path / "nope.sqlite") == []
    assert queries.etl_status(tmp_path / "nope.sqlite")["ok"] is False
    run_etl(root=root)
    conn = queries._ro(_db(root))
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM trades_raw")
    conn.close()


def test_cli_run_status_query(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert etl_main(["--root", str(root), "run"]) == 0
    assert etl_main(["--root", str(root), "query", "pnl", "--period", "week"]) == 0
    printed = capsys.readouterr().out
    assert '"period": "2026-09-07"' in printed


def test_refuses_protected_knowledge_files(root: Path) -> None:
    with pytest.raises(ValueError):
        run_etl(root=root, db=root / "data" / "knowledge" / "agent_rag.sqlite")


def test_synthetic_replay_ledger_and_event_log(tmp_path: Path) -> None:
    """Replay the committed synthetic NIFTY day into an on-disk ledger + event audit, then ETL all of it."""
    pytest.importorskip("desk_ml")
    import desk_ml.paper_scalp as ps
    from desk_ml.event_parity import fixture_replay_kwargs, load_fixture
    from desk_ml.event_path import EventSession
    from events import EventAuditLog
    from ledger import Ledger

    fx = load_fixture(REPO / "packages/desk-ml/tests/fixtures/synthetic_session_nifty.json")
    recon = tmp_path / "data" / "recon"
    # In memory, then copied to disk: an on-disk audit commits once per event (~40k per day).
    ledger = Ledger(":memory:", charges_path=REPO / "config" / "charges.yaml")
    session = EventSession(ledger=ledger, audit=EventAuditLog(ledger.conn))
    saved = ps.load_index_closes, ps.resolve_lot_size
    ps.load_index_closes = lambda u, root=None: {}
    ps.resolve_lot_size = lambda und, root=None: (int(fx["lot_size"]), "fixture")
    try:
        board = ps.replay_paper_scalp(**fixture_replay_kwargs(fx, tmp_path / "engine"), write=False,
                                      event_session=session)
    finally:
        ps.load_index_closes, ps.resolve_lot_size = saved
        session.close()
    disk = tmp_path / "data" / "ledger" / "ledger.sqlite"
    disk.parent.mkdir(parents=True)
    ledger.conn.commit()
    with sqlite3.connect(disk) as dst:
        ledger.conn.backup(dst)
    ledger.close()
    closed = board["closed_trades"]
    recon.mkdir(parents=True, exist_ok=True)
    (recon / "ml_paper_dashboard.json").write_text(json.dumps(board, default=str), encoding="utf-8")
    _write_jsonl(recon / "paper_booked" / f"{fx['session_ist_date']}.jsonl", closed)

    out = run_etl(root=tmp_path)
    assert out["ok"], out["errors"]
    db = _db(tmp_path)
    filled = [r for r in closed if r.get("filled")]
    day = queries.pnl(db)
    assert sum(r["n_trades"] for r in day) == len(filled)  # three sources, each trade once
    assert round(sum(r["net_pnl"] for r in day), 2) == round(sum(r["realized_pnl_inr"] for r in filled), 2)
    st = queries.etl_status(db)["counts"]
    assert st["fills"] == 2 * len(filled) and st["charges"] >= len(filled)
    stages: dict[tuple[str, str], int] = {}
    for r in queries.stage_attribution(db):
        stages[(r["stage"], r["outcome"])] = stages.get((r["stage"], r["outcome"]), 0) + r["n"]
    assert stages[("boss", "ENTRY_APPROVED")] == len(filled)
    assert stages[("desk", "ORDER_FILLED")] == 2 * len(filled)
    votes = queries.analyst_votes(db)
    assert sum(v["n"] for v in votes) == board["event_bus"]["events"]["ANALYST_VOTE"]
    assert queries.model_attribution(db)
    assert all(r["n_exit_measured"] == r["n_trades"] for r in queries.slippage(db))
