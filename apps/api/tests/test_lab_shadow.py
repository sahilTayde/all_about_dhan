import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from api import lab_shadow, ui_feed
from api.main import create_app

FIXTURE = Path(__file__).parent / "fixtures" / "lab_shadow"  # TEST FIXTURE, made-up rows (src=TEST_FIXTURE)
REPO = Path(lab_shadow.__file__).resolve().parents[4]


def _client(tmp_path, monkeypatch, with_file=True):
    if with_file:
        shutil.copytree(FIXTURE / "2026-10-19", tmp_path / "2026-10-19")
    monkeypatch.setattr(lab_shadow, "DATA_DIR", tmp_path)
    return TestClient(create_app())


def test_no_data_without_file(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, with_file=False)
    body = c.get("/research/lab-shadow", params={"day": "2026-10-19"}).json()
    assert body["ok"] is False and body["status"] == "NO_DATA"


def test_reads_csv_and_is_read_only(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    before = (tmp_path / "2026-10-19" / "events.csv").read_bytes()
    body = c.get("/research/lab-shadow", params={"day": "2026-10-19"}).json()
    assert body["ok"] is True and body["in_desk_pnl"] is False and body["in_paper_extra"] is False
    assert body["missing_columns"] == []
    rows = body["rows"]
    assert len(rows) == 6  # '#' fixture comment line skipped
    assert rows[0]["strategy"] == "R01" and rows[0]["strike"] == 25000 and rows[0]["net15"] == 6420.0
    assert rows[0]["entry"] == "09:32" and rows[0]["src"] == "TEST_FIXTURE"
    open_row = rows[-1]
    assert open_row["exit"] is None and open_row["bid_out"] is None and open_row["net15"] is None  # never invented
    assert c.post("/research/lab-shadow").status_code == 405
    assert (tmp_path / "2026-10-19" / "events.csv").read_bytes() == before
    assert sorted(p.name for p in tmp_path.rglob("*")) == ["2026-10-19", "events.csv"]  # nothing written


def test_missing_columns_reported(tmp_path, monkeypatch):
    (tmp_path / "2026-10-19").mkdir()
    (tmp_path / "2026-10-19" / "events.csv").write_text("seen_ist,strategy,status\n2026-10-19 09:51,R01,primary\n")
    c = _client(tmp_path, monkeypatch, with_file=False)
    body = c.get("/research/lab-shadow", params={"day": "2026-10-19"}).json()
    assert body["ok"] is True and "net15" in body["missing_columns"]
    assert body["rows"][0]["status"] == "PRIMARY" and body["rows"][0]["net15"] is None


def test_day_validation_blocks_traversal(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    for bad in ["../secret", "2026-10-19/../../x", "2026-1-3", "2026-10-19.csv", "2026-13-40", "%2e%2e", "2026-10-19/events"]:
        assert c.get("/research/lab-shadow", params={"day": bad}).status_code == 422
    assert lab_shadow.load_day("..", tmp_path)["status"] == "NO_DATA"  # path check even if validation is bypassed


def test_no_desk_total_reads_lab_shadow(tmp_path, monkeypatch):
    rows = [{"trade_id": "t1", "book_id": "R01_PDIV_5_ALL_H20", "day": "2026-10-19", "closed_ts": 1, "status": "CLOSED",
             "realized_pnl_inr": -500.0, "gross_pnl_inr": -400.0, "charges_inr": 100.0, "exit_reason": "TIME"}]
    before = ui_feed.day_summaries([dict(r) for r in rows])
    _client(tmp_path, monkeypatch).get("/research/lab-shadow", params={"day": "2026-10-19"})
    assert ui_feed.day_summaries([dict(r) for r in rows]) == before
    # desk P&L / board / paper_booked / paper_extra code never mentions the lab shadow feed
    totals = [Path(ui_feed.__file__), REPO / "apps/api/src/api/desk_merge.py", REPO / "apps/api/src/api/premium_bind.py",
              *sorted((REPO / "scripts" / "paper_extra").glob("*.py"))]
    for f in totals:
        if f.is_file():
            assert "lab_shadow" not in f.read_text() and "lab-shadow" not in f.read_text(), f
    # and the lab shadow module imports nothing from them
    src = Path(lab_shadow.__file__).read_text()
    for name in ("ui_feed", "desk_merge", "premium_bind", "paper_booked", "paper_extra", "store"):
        assert f"import {name}" not in src and f"api.{name}" not in src, name
