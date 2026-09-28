"""REG-08a/b: ETL skips bad files and lines, counts them, and a rerun is idempotent."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from warehouse.etl import list_ingest_errors, run_etl

TS = "2026-09-25T10:00:00+05:30"
SESSION = "2026-09-25"


def _good(signal_id: str) -> str:
    return json.dumps(
        {"event_type": "SIGNAL", "event_ts": TS, "payload": {"signal_id": signal_id}}
    )


def test_reg_08a_bad_files_and_lines_skipped_counted_logged(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    goods = "\n".join(_good(f"ok-{i}") for i in range(1, 39))
    (src / "events.jsonl").write_text(
        goods + '\n{not-json\n["wrong-schema"]\n', encoding="utf-8"
    )
    (src / "recorder.jsonl").write_text("", encoding="utf-8")
    (src / "bench.jsonl.gz").write_bytes(gzip.compress(b'{"trade_id":"x"}\n')[:8])
    dest = tmp_path / "wh"
    report = run_etl(src=src, dest=dest, session=SESSION)
    assert report.loaded_rows["events"] == 38
    assert report.skipped_lines >= 2
    assert report.skipped_files >= 1
    assert report.ingest_errors >= 3
    paths = {e["path"] for e in list_ingest_errors(dest)}
    assert any(p.endswith("events.jsonl") for p in paths)
    rows = [
        json.loads(x)
        for x in (dest / "parquet" / "events" / f"date={SESSION}" / "part-000.jsonl")
        .read_text()
        .splitlines()
    ]
    assert [r["payload"]["signal_id"] for r in rows] == [
        f"ok-{i}" for i in range(1, 39)
    ]


def test_reg_08b_rerun_is_idempotent(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    goods = "\n".join(_good(f"ok-{i}") for i in range(19))
    (src / "events.jsonl").write_text(goods + "\n{bad\n", encoding="utf-8")
    dest = tmp_path / "wh"
    a = run_etl(src=src, dest=dest, session=SESSION)
    b = run_etl(src=src, dest=dest, session=SESSION)
    assert a.dest_hash == b.dest_hash
    assert a.ingest_errors == b.ingest_errors == len(list_ingest_errors(dest))
    assert b.files_read == 0
