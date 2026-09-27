"""V2-18 warehouse ETL acceptance (paper fixtures; no network; no data/ writes)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from warehouse.etl import attribution_chain, run_etl


def _write(path: Path, rows: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _src(tmp: Path) -> Path:
    src = tmp / "src"
    src.mkdir()
    db = sqlite3.connect(src / "ledger.sqlite")
    db.executescript(
        """
        CREATE TABLE orders (client_order_id TEXT, signal_id TEXT, decision_id TEXT, symbol TEXT);
        CREATE TABLE trades (trade_id TEXT, signal_id TEXT, entry_client_order_id TEXT, net_pnl REAL, exit_reason TEXT, strategy_id TEXT);
        INSERT INTO orders VALUES ('aadorder000000000000000001','sig-1','dec-1','NIFTY 24500 CE');
        INSERT INTO trades VALUES ('tr-1','sig-1','aadorder000000000000000001',120.5,'TIME_STOP','TEST-CROSS');
        """
    )
    db.commit()
    db.close()
    _write(
        src / "events.jsonl",
        [
            {"event_type": "SIGNAL", "payload": {"signal_id": "sig-1", "strategy_id": "TEST-CROSS"}},
            {"event_type": "DECISION", "payload": {"decision_id": "dec-1", "signal_ids": ["sig-1"]}},
            {"event_type": "ENTRY_PLAN", "payload": {"signal_id": "sig-1", "action": "CHASE", "zone": "fvg", "strategy_id": "TEST-CROSS"}},
            {"event_type": "ENTRY_PLAN_RESULT", "payload": {"signal_id": "sig-1", "action": "CHASE", "zone": "fvg", "strategy_id": "TEST-CROSS", "status": "FILLED", "giveback_5m_pts": 1.5}},
        ],
    )
    _write(src / "tape" / "depth.jsonl", [{"event_type": "DEPTH_QUOTE", "payload": {"instrument_id": "NSE_FNO:NIFTY:2026-09-29:24500:CE", "bid": 80, "ask": 80.2}}])
    _write(
        src / "tape" / "quotes.jsonl",
        [
            {"event_type": "QUOTE_SNAPSHOT", "payload": {"instrument_id": "i", "rule": "ATM", "spread": 0.20}},
            {"event_type": "QUOTE_SNAPSHOT", "payload": {"instrument_id": "i", "rule": "ITM100", "spread": 0.30}},
        ],
    )
    _write(
        src / "tape" / "oi_cadence.jsonl",
        [{"event_type": "OI_CADENCE", "payload": {"instrument_id": "i", "oi_updates": 4, "median_gap_s": 12.0, "p90_gap_s": 20.0}}],
    )
    _write(src / "recorder.jsonl", [{"underlying": "NIFTY", "close": 24500}])
    _write(src / "bench.jsonl", [{"trade_id": "legacy-1", "net_pnl": -10}])
    _write(src / "forward.jsonl", [{"spec_id": "E1", "signal_id": "sig-1", "leg": "chosen", "net_depth_inr": 80}])
    return src


def test_etl_idempotent_second_run_changes_nothing(tmp_path: Path) -> None:
    src, dest = _src(tmp_path), tmp_path / "wh"
    a = run_etl(src=src, dest=dest, session="2026-09-26")
    b = run_etl(src=src, dest=dest, session="2026-09-26")
    assert a.dest_hash == b.dest_hash
    assert a.loaded_rows == b.loaded_rows
    assert b.files_read == 0 and b.files_reused == a.files_seen


def test_etl_incremental(tmp_path: Path) -> None:
    src, dest = _src(tmp_path), tmp_path / "wh"
    first = run_etl(src=src, dest=dest, session="2026-09-26")
    _write(src / "recorder.jsonl", [{"underlying": "NIFTY", "close": 24500}, {"underlying": "SENSEX", "close": 81000}])
    second = run_etl(src=src, dest=dest, session="2026-09-26")
    assert second.files_read == 1
    assert second.loaded_rows["recorder"] == 2
    assert second.loaded_rows["events"] == first.loaded_rows["events"]


def test_row_counts_equal_the_sources(tmp_path: Path) -> None:
    src, dest = _src(tmp_path), tmp_path / "wh"
    r = run_etl(src=src, dest=dest, session="2026-09-26")
    for table, n in r.source_rows.items():
        assert r.loaded_rows[table] == n


def test_attribution_query_full_chain(tmp_path: Path) -> None:
    src, dest = _src(tmp_path), tmp_path / "wh"
    run_etl(src=src, dest=dest, session="2026-09-26")
    chain = attribution_chain(dest)
    assert chain == [{"signal_id": "sig-1", "decision_id": "dec-1", "client_order_id": "aadorder000000000000000001", "trade_id": "tr-1", "net_pnl": 120.5}]


def test_daily_oi_cadence_and_spread_by_moneyness(tmp_path: Path) -> None:
    src, dest = _src(tmp_path), tmp_path / "wh"
    r = run_etl(src=src, dest=dest, session="2026-09-26")
    assert r.loaded_rows["oi_cadence"] == 1
    assert r.loaded_rows["spread_by_moneyness"] == 2
    oi = json.loads((dest / "parquet" / "oi_cadence" / "date=2026-09-26" / "part-000.jsonl").read_text().splitlines()[0])
    assert oi["oi_updates"] == 4 and oi["median_gap_s"] == 12.0
    rules = {json.loads(x)["rule"] for x in (dest / "parquet" / "spread_by_moneyness" / "date=2026-09-26" / "part-000.jsonl").read_text().splitlines()}
    assert rules == {"ATM", "ITM100"}
    loc = json.loads((dest / "parquet" / "entry_location_daily" / "date=2026-09-26" / "part-000.jsonl").read_text().splitlines()[0])
    assert loc["action"] == "CHASE" and loc["zone"] == "fvg" and loc["fill_rate"] == 1.0 and loc["net"] == 120.5
