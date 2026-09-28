"""V2-18 warehouse ETL acceptance (paper fixtures; no network; no data/ writes)."""

from __future__ import annotations

import json
import os
import sqlite3
import tracemalloc
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from warehouse.calendar import is_nse_trading_day, nse_holidays_2026, trading_date_from_now
from warehouse.etl import WarehouseFailClosed, attribution_chain, main, run_etl

IST_TS = "2026-09-25T10:00:00+05:30"
SESSION = "2026-09-25"


def _write(path: Path, rows: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _row(event_type: str, payload: dict[str, object], ts: str = IST_TS) -> dict[str, object]:
    return {"event_type": event_type, "event_ts": ts, "payload": payload}


def _src(tmp: Path) -> Path:
    src = tmp / "src"
    src.mkdir()
    db = sqlite3.connect(src / "ledger.sqlite")
    db.executescript(
        f"""
        CREATE TABLE orders (client_order_id TEXT, signal_id TEXT, decision_id TEXT, symbol TEXT, created_at TEXT);
        CREATE TABLE trades (trade_id TEXT, signal_id TEXT, entry_client_order_id TEXT, net_pnl REAL, exit_reason TEXT, strategy_id TEXT, created_at TEXT);
        INSERT INTO orders VALUES ('aadorder000000000000000001','sig-1','dec-1','NIFTY 24500 CE','{IST_TS}');
        INSERT INTO trades VALUES ('tr-1','sig-1','aadorder000000000000000001',120.5,'TIME_STOP','TEST-CROSS','{IST_TS}');
        """
    )
    db.commit()
    db.close()
    _write(
        src / "events.jsonl",
        [
            _row("SIGNAL", {"signal_id": "sig-1", "strategy_id": "TEST-CROSS"}),
            _row("DECISION", {"decision_id": "dec-1", "signal_ids": ["sig-1"]}),
            _row("ENTRY_PLAN", {"signal_id": "sig-1", "action": "CHASE", "zone": "fvg", "strategy_id": "TEST-CROSS"}),
            _row(
                "ENTRY_PLAN_RESULT",
                {
                    "signal_id": "sig-1",
                    "action": "CHASE",
                    "zone": "fvg",
                    "strategy_id": "TEST-CROSS",
                    "status": "FILLED",
                    "giveback_5m_pts": 1.5,
                },
            ),
        ],
    )
    _write(
        src / "tape" / "depth.jsonl",
        [_row("DEPTH_QUOTE", {"instrument_id": "NSE_FNO:NIFTY:2026-09-29:24500:CE", "bid": 80, "ask": 80.2})],
    )
    _write(
        src / "tape" / "quotes.jsonl",
        [
            _row("QUOTE_SNAPSHOT", {"instrument_id": "i", "rule": "ATM", "spread": 0.20}),
            _row("QUOTE_SNAPSHOT", {"instrument_id": "i", "rule": "ITM100", "spread": 0.30}),
        ],
    )
    _write(
        src / "tape" / "oi_cadence.jsonl",
        [_row("OI_CADENCE", {"instrument_id": "i", "oi_updates": 4, "median_gap_s": 12.0, "p90_gap_s": 20.0})],
    )
    _write(src / "recorder.jsonl", [{"underlying": "NIFTY", "close": 24500, "event_ts": IST_TS}])
    _write(src / "bench.jsonl", [{"trade_id": "legacy-1", "net_pnl": -10, "event_ts": IST_TS}])
    _write(
        src / "forward.jsonl",
        [{"spec_id": "E1", "signal_id": "sig-1", "leg": "chosen", "net_depth_inr": 80, "event_ts": IST_TS}],
    )
    return src


def test_etl_idempotent_second_run_changes_nothing(tmp_path: Path) -> None:
    src, dest = _src(tmp_path), tmp_path / "wh"
    a = run_etl(src=src, dest=dest, session=SESSION)
    b = run_etl(src=src, dest=dest, session=SESSION)
    assert a.dest_hash == b.dest_hash
    assert a.loaded_rows == b.loaded_rows
    assert b.files_read == 0 and b.files_reused == a.files_seen


def test_etl_incremental(tmp_path: Path) -> None:
    src, dest = _src(tmp_path), tmp_path / "wh"
    first = run_etl(src=src, dest=dest, session=SESSION)
    _write(
        src / "recorder.jsonl",
        [
            {"underlying": "NIFTY", "close": 24500, "event_ts": IST_TS},
            {"underlying": "SENSEX", "close": 81000, "event_ts": IST_TS},
        ],
    )
    second = run_etl(src=src, dest=dest, session=SESSION)
    assert second.files_read == 1
    assert second.loaded_rows["recorder"] == 2
    assert second.loaded_rows["events"] == first.loaded_rows["events"]


def test_row_counts_equal_the_sources(tmp_path: Path) -> None:
    src, dest = _src(tmp_path), tmp_path / "wh"
    r = run_etl(src=src, dest=dest, session=SESSION)
    for table, n in r.source_rows.items():
        assert r.loaded_rows[table] == n
    event_lines = 0
    for part in (dest / "parquet" / "events").glob("date=*/part-000.jsonl"):
        event_lines += sum(1 for line in part.read_text(encoding="utf-8").splitlines() if line)
    assert event_lines == r.source_rows["events"]


def test_attribution_query_full_chain(tmp_path: Path) -> None:
    src, dest = _src(tmp_path), tmp_path / "wh"
    run_etl(src=src, dest=dest, session=SESSION)
    chain = attribution_chain(dest)
    assert chain == [
        {
            "signal_id": "sig-1",
            "decision_id": "dec-1",
            "client_order_id": "aadorder000000000000000001",
            "trade_id": "tr-1",
            "net_pnl": 120.5,
        }
    ]


def test_daily_oi_cadence_and_spread_by_moneyness(tmp_path: Path) -> None:
    src, dest = _src(tmp_path), tmp_path / "wh"
    r = run_etl(src=src, dest=dest, session=SESSION)
    assert r.loaded_rows["oi_cadence"] == 1
    assert r.loaded_rows["spread_by_moneyness"] == 2
    oi = json.loads(
        (dest / "parquet" / "oi_cadence" / f"date={SESSION}" / "part-000.jsonl").read_text().splitlines()[0]
    )
    assert oi["oi_updates"] == 4 and oi["median_gap_s"] == 12.0
    rules = {
        json.loads(x)["rule"]
        for x in (dest / "parquet" / "spread_by_moneyness" / f"date={SESSION}" / "part-000.jsonl")
        .read_text()
        .splitlines()
    }
    assert rules == {"ATM", "ITM100"}
    loc = json.loads(
        (dest / "parquet" / "entry_location_daily" / f"date={SESSION}" / "part-000.jsonl").read_text().splitlines()[0]
    )
    assert loc["action"] == "CHASE" and loc["zone"] == "fvg" and loc["fill_rate"] == 1.0 and loc["net"] == 120.5


def test_future_row_lands_in_its_own_date_partition(tmp_path: Path) -> None:
    src = _src(tmp_path)
    _write(
        src / "events.jsonl",
        [
            _row("SIGNAL", {"signal_id": "fri-in"}, "2026-09-25T10:00:00+05:30"),
            _row("SIGNAL", {"signal_id": "fri-late"}, "2026-09-25T16:00:00+05:30"),
            _row("SIGNAL", {"signal_id": "mon"}, "2026-09-28T10:00:00+05:30"),
            _row(
                "ENTRY_PLAN",
                {"signal_id": "late-plan", "action": "CHASE", "zone": "fvg", "strategy_id": "X"},
                "2026-09-25T16:05:00+05:30",
            ),
        ],
    )
    _write(
        src / "tape" / "quotes.jsonl",
        [
            _row("QUOTE_SNAPSHOT", {"instrument_id": "i", "rule": "ATM", "spread": 0.20}, "2026-09-25T10:00:00+05:30"),
            _row(
                "QUOTE_SNAPSHOT", {"instrument_id": "i", "rule": "ITM100", "spread": 9.99}, "2026-09-25T16:00:00+05:30"
            ),
        ],
    )
    dest = tmp_path / "wh"
    r = run_etl(src=src, dest=dest, session=SESSION)
    fri = [
        json.loads(x)
        for x in (dest / "parquet" / "events" / "date=2026-09-25" / "part-000.jsonl").read_text().splitlines()
    ]
    mon = [
        json.loads(x)
        for x in (dest / "parquet" / "events" / "date=2026-09-28" / "part-000.jsonl").read_text().splitlines()
    ]
    assert {row["payload"]["signal_id"] for row in fri} == {"fri-in", "fri-late", "late-plan"}
    assert {row["payload"]["signal_id"] for row in mon} == {"mon"}
    by_id = {row["payload"]["signal_id"]: row["in_session"] for row in fri + mon}
    assert by_id == {"fri-in": True, "fri-late": False, "late-plan": False, "mon": True}
    assert not (dest / "parquet" / "events" / "date=2026-09-26").exists()
    spread_path = dest / "parquet" / "spread_by_moneyness" / "date=2026-09-25" / "part-000.jsonl"
    rules = {json.loads(x)["rule"] for x in spread_path.read_text().splitlines()}
    assert rules == {"ATM"}
    assert not (dest / "parquet" / "entry_location_daily" / "date=2026-09-25").exists()
    assert r.loaded_rows["events"] == 4


def test_sunday_and_2026_10_02_refused(tmp_path: Path) -> None:
    src = _src(tmp_path)
    assert date(2026, 10, 2) in nse_holidays_2026()
    assert not is_nse_trading_day(date(2026, 9, 27))
    assert not is_nse_trading_day(date(2026, 10, 2))
    for session, dest_name in (("2026-09-27", "sun"), ("2026-10-02", "gandhi")):
        dest = tmp_path / dest_name
        assert main(["--src", str(src), "--out", str(dest), "--session", session]) == 2
        assert not dest.exists()


def test_ct_evening_maps_to_ist_date(tmp_path: Path) -> None:
    now = datetime(2026, 9, 24, 19, 0, tzinfo=ZoneInfo("America/Chicago"))
    assert trading_date_from_now(now).isoformat() == "2026-09-25"
    src, dest = _src(tmp_path), tmp_path / "wh"
    report = run_etl(src=src, dest=dest, session=None, now=now)
    assert report.session == "2026-09-25"
    assert (dest / "parquet" / "events" / "date=2026-09-25" / "part-000.jsonl").is_file()
    sat = datetime(2026, 9, 25, 19, 0, tzinfo=ZoneInfo("America/Chicago"))
    assert trading_date_from_now(sat).isoformat() == "2026-09-26"
    assert main(["--src", str(src), "--out", str(tmp_path / "sat"), "--now", sat.isoformat()]) == 2
    assert not (tmp_path / "sat").exists()


def test_bounded_memory_tracemalloc_under_2mb(tmp_path: Path) -> None:
    src = _src(tmp_path)
    line = json.dumps({"underlying": "NIFTY", "close": 24500, "event_ts": IST_TS}) + "\n"
    with (src / "recorder.jsonl").open("w", encoding="utf-8") as fh:
        for _ in range(50_000):
            fh.write(line)
    dest = tmp_path / "wh"
    tracemalloc.start()
    report = run_etl(src=src, dest=dest, session=SESSION)
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert report.loaded_rows["recorder"] == 50_000
    assert peak < 2 * 1024 * 1024


def test_all_garbage_exits_nonzero(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "events.jsonl").write_text("{bad\n{also-bad\n", encoding="utf-8")
    dest = tmp_path / "wh"
    assert main(["--src", str(src), "--out", str(dest), "--session", SESSION]) == 1
    with pytest.raises(WarehouseFailClosed):
        run_etl(src=src, dest=tmp_path / "wh2", session=SESSION)


def test_tapes_open_rdonly_and_refuse_dest_under_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    flags: list[tuple[str, int]] = []
    real_open = os.open

    def wrapped(path: str | bytes | os.PathLike[str], flag: int, *args: object, **kwargs: object) -> int:
        flags.append((os.fsdecode(path), flag))
        return real_open(path, flag, *args, **kwargs)

    monkeypatch.setattr(os, "open", wrapped)
    src = _src(tmp_path)
    run_etl(src=src, dest=tmp_path / "wh", session=SESSION)
    tape = (src / "tape" / "quotes.jsonl").resolve()
    tape_flags = [flag for path, flag in flags if Path(path).resolve() == tape]
    assert tape_flags and all(flag == os.O_RDONLY for flag in tape_flags)
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    dest = repo / "data" / "wh"
    dest.mkdir(parents=True)
    with pytest.raises(ValueError, match="checkout data"):
        run_etl(src=src, dest=dest, session=SESSION)
