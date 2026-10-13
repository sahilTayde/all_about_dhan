import json

from fastapi.testclient import TestClient

from api import background_test, ui_feed
from api.main import create_app

ROW = {"source": "background-test", "label": "Background test (not traded)", "paper_only": True, "in_desk_pnl": False,
       "day": "2026-10-13", "summary": {"closed_unique": 1, "net_inr_1_5x": 1000.0, "failed": 0},
       "trades": [{"strategy": "B2", "side": "CE", "strike": 22300, "net_inr_1_5x": 1000.0, "status": "CLOSED",
                   "verified": "PASS", "duplicate_of": None, "count_in_total": True}]}


def test_no_data_without_file(tmp_path, monkeypatch):
    monkeypatch.setattr(background_test, "DATA_DIR", tmp_path)
    c = TestClient(create_app())
    body = c.get("/research/background-test", params={"day": "2026-10-13"}).json()
    assert body["ok"] is False and body["status"] == "NO_DATA"


def test_reads_file_and_is_read_only(tmp_path, monkeypatch):
    monkeypatch.setattr(background_test, "DATA_DIR", tmp_path)
    (tmp_path / "2026-10-13.json").write_text(json.dumps({**ROW, "in_desk_pnl": True}))
    c = TestClient(create_app())
    body = c.get("/research/background-test", params={"day": "2026-10-13"}).json()
    assert body["ok"] is True and body["in_desk_pnl"] is False  # forced off whatever the file says
    assert body["trades"][0]["strategy"] == "B2"
    assert c.post("/research/background-test").status_code == 405


def test_day_validation_blocks_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(background_test, "DATA_DIR", tmp_path)
    c = TestClient(create_app())
    for bad in ["../secret", "2026-10-13/../../x", "2026-1-3", "2026-10-13.json", "2026-13-40", "%2e%2e"]:
        assert c.get("/research/background-test", params={"day": bad}).status_code == 422


def test_desk_day_net_unchanged_with_file(tmp_path, monkeypatch):
    rows = [{"trade_id": "t1", "book_id": "R01_PDIV_5_ALL_H20", "day": "2026-10-13", "closed_ts": 1, "status": "CLOSED",
             "realized_pnl_inr": -500.0, "gross_pnl_inr": -400.0, "charges_inr": 100.0, "exit_reason": "TIME"}]
    before = ui_feed.day_summaries([dict(r) for r in rows])
    monkeypatch.setattr(background_test, "DATA_DIR", tmp_path)
    (tmp_path / "2026-10-13.json").write_text(json.dumps(ROW))
    after = ui_feed.day_summaries([dict(r) for r in rows])
    assert before == after
    assert "background_test" not in open(ui_feed.__file__).read()  # P&L code never reads it
