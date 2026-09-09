from backtest_engine.indicators import Bar
from backtest_engine.live_signals import PaperSignalEngine, club_gr_leans
from backtest_engine.paper_watch import append_paper_event, paper_watch_dir


def test_club_gr_leans_empty_on_short_series():
    bars = [
        Bar(ts=1_000 + i * 180, open=100, high=101, low=99, close=100 + i * 0.1, volume=1)
        for i in range(5)
    ]
    leans = club_gr_leans(bars)
    assert len(leans) == len(bars)
    assert all(x == "SKIP" for x in leans)


def test_paper_engine_exposes_parallel_club_book():
    eng = PaperSignalEngine()
    # NIFTY security_id 13
    for i in range(40):
        eng.ingest(
            {
                "security_id": 13,
                "fields": {
                    "ltp": 24000 + i,
                    "volume": 1,
                    "last_trade_time_epoch": 1_700_000_000 + i * 60,
                },
            }
        )
    snap = eng.snapshot()
    assert snap["orders"] == "refused"
    assert snap["customer_default_mix"] == "MIX-DEFAULT-BUY"
    assert "MIX-CLUB-GR" not in snap["paper_watch_mixes"]
    assert "MIX-CF-OKALA-IN-H-CROSS" not in snap.get("paper_watch_mixes", [])
    assert "MIX-CLUB-GR" in snap["books"]
    assert "NIFTY" in snap["books"]["MIX-CLUB-GR"]
    assert snap["books"]["MIX-CLUB-GR"]["NIFTY"]["paper_watch"] is False
    assert snap["books"]["MIX-CLUB-GR"]["NIFTY"].get("working_path") == "PARKED"
    assert snap["books"]["MIX-DEFAULT-BUY"]["NIFTY"]["customer_default"] is True


def test_append_paper_event_writes_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "backtest_engine.paper_watch.repo_root", lambda: tmp_path
    )
    path = append_paper_event("MIX-CLUB-GR", {"underlying": "NIFTY", "lean": "CE"})
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "MIX-CLUB-GR" == "MIX-CLUB-GR"
    assert "CE" in text
    assert paper_watch_dir("MIX-CLUB-GR").exists()
