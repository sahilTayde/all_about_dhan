"""REG-08a/b: ETL skips bad files and lines, counts them, and a rerun is idempotent."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from warehouse.etl import list_ingest_errors, run_etl


def test_reg_08a_bad_files_and_lines_skipped_counted_logged(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "events.jsonl").write_text(
        '{"event_type":"SIGNAL","payload":{"signal_id":"ok-1"}}\n'
        "{not-json\n"
        '["wrong-schema"]\n'
        '{"event_type":"SIGNAL","payload":{"signal_id":"ok-2"}}\n',
        encoding="utf-8",
    )
    (src / "recorder.jsonl").write_text("", encoding="utf-8")
    (src / "bench.jsonl.gz").write_bytes(gzip.compress(b'{"trade_id":"x"}\n')[:8])
    dest = tmp_path / "wh"
    report = run_etl(src=src, dest=dest, session="2026-09-26")
    assert report.loaded_rows["events"] == 2
    assert report.skipped_lines >= 2
    assert report.skipped_files >= 1
    assert report.ingest_errors >= 3
    paths = {e["path"] for e in list_ingest_errors(dest)}
    assert any(p.endswith("events.jsonl") for p in paths)
    rows = [json.loads(x) for x in (dest / "parquet" / "events" / "date=2026-09-26" / "part-000.jsonl").read_text().splitlines()]
    assert [r["payload"]["signal_id"] for r in rows] == ["ok-1", "ok-2"]


def test_reg_08b_rerun_is_idempotent(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "events.jsonl").write_text('{"event_type":"SIGNAL","payload":{"signal_id":"ok"}}\n{bad\n', encoding="utf-8")
    dest = tmp_path / "wh"
    a = run_etl(src=src, dest=dest, session="2026-09-26")
    b = run_etl(src=src, dest=dest, session="2026-09-26")
    assert a.dest_hash == b.dest_hash
    assert a.ingest_errors == b.ingest_errors == len(list_ingest_errors(dest))
    assert b.files_read == 0
