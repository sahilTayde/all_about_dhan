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
    assert len(rows) == 7  # '#' fixture comment line skipped
    assert rows[0]["strategy"] == "R01" and rows[0]["strike"] == 25000 and rows[0]["net15"] == 6420.0
    assert rows[0]["seen_ist"] == "09:51" and rows[0]["entry"] == "09:32" and rows[0]["src"] == "TEST_FIXTURE"
    assert rows[0]["rand15"] == -310.0 and rows[0]["situation"] == "trend day" and rows[0]["data_gap"] is None
    assert rows[2]["data_gap"] == "ask missing 10:05-10:09" and rows[2]["rand15"] is None  # empty random never filled
    open_row = rows[-1]
    assert open_row["exit"] is None and open_row["bid_out"] is None and open_row["net15"] is None  # never invented
    assert open_row["rand15"] is None
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


REAL_HEADER = ("seen_ist,lag_min,strategy,family,status,und,side,strike,sig,entry,exit,ask_in,bid_out,net15,rand15,"
               "data_gap,situation,reason,src")
REAL_LINE = ('10:45,21,R01_PDIV_5_ALL_H20,trend,PRIMARY,NIFTY,CE,23100,10:24,10:25,10:45,55.65,41.1,-9629.69,,,,'
             '"slot rule R01_PDIV_5_ALL_H20 signal 10:24, exit time",trades')  # verbatim from the real 2026-10-19 feed


def test_real_line_bare_hhmm():
    rows, missing = lab_shadow.parse_csv(REAL_HEADER + "\n" + REAL_LINE + "\n")
    assert missing == [] and len(rows) == 1
    r = rows[0]
    assert (r["seen_ist"], r["sig"], r["entry"], r["exit"]) == ("10:45", "10:24", "10:25", "10:45")
    assert (r["strategy"], r["status"], r["und"], r["side"], r["strike"]) == ("R01_PDIV_5_ALL_H20", "PRIMARY", "NIFTY", "CE", 23100)
    assert (r["ask_in"], r["bid_out"], r["net15"], r["lag_min"]) == (55.65, 41.1, -9629.69, 21)
    assert r["rand15"] is None and r["data_gap"] is None and r["situation"] is None  # empty stays empty
    assert r["reason"] == "slot rule R01_PDIV_5_ALL_H20 signal 10:24, exit time" and r["src"] == "trades"


def test_full_datetime_form_still_accepted():
    line = REAL_LINE.replace("10:45,21,", "2026-10-19 10:45,21,", 1)
    rows, _ = lab_shadow.parse_csv(REAL_HEADER + "\n" + line)
    assert rows[0]["seen_ist"] == "2026-10-19 10:45" and rows[0]["net15"] == -9629.69


def test_comparison_inputs_pass_through_unchanged():
    """The web labels rand15 by reason / strategy / src / family, so the API must hand those over verbatim."""
    lines = [  # F2 line is verbatim from the real 2026-10-19 feed; the rest follow live_runner.py's row shapes
        "13:05,160,F2_UNWIND,exit-overlay,WATCH,NIFTY,,,10:25,10:25,10:32,55.65,,-1852.17,-9629.69,,,F2 on R01_PDIV_5_ALL_H20 hit=1 (vs base),f2unwind",
        "13:05,20,QT:QT_P15,exit-overlay,PARKED,NIFTY,CE,23100,10:25,10:25,10:45,55.65,,900,300,,,QT_P15 on R01_PDIV_5_ALL_H20 (vs random exit),quicktarget",
        "13:05,20,ROUTER:F2,exit-overlay,WATCH,NIFTY,CE,,,,,,,70,10,,trend,router arm F2 in trend,parked_router",
        "13:05,20,B2,breakout,WATCH,NIFTY,CE,,11:31,11:31,11:52,80,90,700,-250,,,twoday cell B2_c3 fired 11:31,twoday",
        "13:05,20,GBV:GB30,exit-overlay,WATCH,NIFTY,CE,23100,11:09,11:09,11:29,72.65,60,1200,150,,,giveback GB30 on R01_PDIV_5_ALL_H20,gbv",
    ]
    rows, missing = lab_shadow.parse_csv(REAL_HEADER + "\n" + "\n".join(lines))
    assert missing == [] and len(rows) == 5
    assert [(r["strategy"], r["family"], r["src"], r["rand15"]) for r in rows] == [
        ("F2_UNWIND", "exit-overlay", "f2unwind", -9629.69), ("QT:QT_P15", "exit-overlay", "quicktarget", 300.0),
        ("ROUTER:F2", "exit-overlay", "parked_router", 10.0), ("B2", "breakout", "twoday", -250.0),
        ("GBV:GB30", "exit-overlay", "gbv", 150.0)]
    assert rows[0]["reason"] == "F2 on R01_PDIV_5_ALL_H20 hit=1 (vs base)" and rows[0]["side"] is None and rows[0]["strike"] is None
    assert rows[2]["entry"] is None and rows[2]["situation"] == "trend"
    assert "cmp_kind" not in rows[0]  # the API never guesses the kind; display only


REAL_V1 = Path(__file__).parent / "fixtures" / "lab_shadow_real_v1" / "events_2026-10-19.csv"  # real lines, old format
REAL_V2 = Path(__file__).parent / "fixtures" / "lab_shadow_real_v2" / "events_2026-10-19.csv"  # real lines, new format


def _serve(tmp_path, monkeypatch, src):
    (tmp_path / "2026-10-19").mkdir()
    shutil.copy(src, tmp_path / "2026-10-19" / "events.csv")
    monkeypatch.setattr(lab_shadow, "DATA_DIR", tmp_path)
    return TestClient(create_app()).get("/research/lab-shadow", params={"day": "2026-10-19"}).json()


def test_real_v1_file_old_format(tmp_path, monkeypatch):
    body = _serve(tmp_path, monkeypatch, REAL_V1)
    assert body["ok"] is True and body["format"] == "v1" and body["missing_columns"] == []
    assert len(body["rows"]) == 7 and all("trade_id" not in r and "cmp_kind" not in r for r in body["rows"])


def test_real_v2_file_new_format(tmp_path, monkeypatch):
    body = _serve(tmp_path, monkeypatch, REAL_V2)
    assert body["ok"] is True and body["format"] == "v2" and body["missing_columns"] == []
    rows = body["rows"]
    assert len(rows) == 10
    assert rows[0]["trade_id"] == "NIFTY_CE_23100_10:25_R01_PDIV_5_ALL_H20" and rows[0]["cmp_kind"] == "none"
    assert rows[1]["trade_id"] == "NIFTY_CE_23100_10:25_B3a_PDIV5_VOLHIGH"  # id ends in the rule name
    assert rows[2]["trade_id"] == "NIFTY_CE__09:52_MIX_ALONE" and rows[2]["strike"] is None
    f2 = rows[3]
    assert (f2["strategy"], f2["cmp_kind"], f2["trade_id"]) == ("F2_UNWIND", "base", "NIFTY_CE_23100_10:25_R01_PDIV_5_ALL_H20")
    assert f2["side"] is None and f2["rand15"] == -9629.69  # overlay carries its base's id; base net in rand15


def test_v2_only_one_new_column_stays_v1():
    rows, missing, fmt = lab_shadow.parse_csv_fmt(REAL_HEADER + ",trade_id\n" + REAL_LINE + ",X_1\n")
    assert fmt == "v1" and missing == [] and rows[0]["trade_id"] == "X_1" and "cmp_kind" not in rows[0]
