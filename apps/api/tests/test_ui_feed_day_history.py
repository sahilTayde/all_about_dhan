"""2026-10-19: past days stay on /desk from research_rules day files, keyed by (day, trade_id),
with no double counting against backfilled paper_booked files, and Oct 19 hindsight fills excluded."""
import json


def _rr_row(tid, day, hhmm, pnl, **extra):
    return {"trade_id": tid, "book_id": tid.split("-")[1], "underlying": "NIFTY", "side": "PE", "status": "CLOSED",
            "entry": 100.0, "exit": 110.0, "realized_pnl_inr": pnl, "gross_pnl_inr": pnl + 500, "charges_inr": 500,
            "entry_min": hhmm, "opened_ist": f"{day}T{hhmm}:00+05:30", "filled": True, "shadow": False,
            "desk_status": "TRADED", "exit_reason": "TARGET", **extra}


def _setup(root):
    recon = root / "data" / "recon"
    (recon / "research_rules").mkdir(parents=True)
    (recon / "paper_booked").mkdir(parents=True)
    # same bare id on two different days must stay two trades
    d16 = [_rr_row("RR-PX_B2-NIFTY-PE-0915", "2026-10-16", "09:16", 1000.0),
           _rr_row("RR-PX_R07-NIFTY-CE-1002", "2026-10-16", "10:03", -400.0)]
    (recon / "research_rules" / "2026-10-16.json").write_text(json.dumps({"closed": d16, "open": []}))
    # Oct 16 also backfilled into paper_booked with a "-<day>" suffix: must not double count
    with open(recon / "paper_booked" / "2026-10-16.jsonl", "w") as f:
        for r in d16:
            f.write(json.dumps({**r, "trade_id": r["trade_id"] + "-2026-10-16"}) + "\n")
    d19 = [_rr_row("RR-PX_B2-NIFTY-PE-0915", "2026-10-19", "09:20", 5000.0),
           _rr_row("RR-PX_EP010-NIFTY-CE-0944", "2026-10-19", "09:45", 300.0),
           _rr_row("RR-PX_ENG_5-NIFTY-PE-0949", "2026-10-19", "09:50", 2000.0),
           _rr_row("RR-PX_IB_15-NIFTY-PE-1259", "2026-10-19", "13:00", -700.0)]
    (recon / "research_rules" / "2026-10-19.json").write_text(json.dumps({"closed": d19, "open": []}))


def test_past_days_from_research_rules_once_and_hindsight_excluded(tmp_path) -> None:
    from api.ui_feed import _today_split, day_summaries, history_rows

    _setup(tmp_path)
    board = {"session_ist_date": "2026-10-20", "closed_trades": []}  # the board has moved on
    rows = history_rows(tmp_path, board, events={})
    days = {d["day"]: d for d in day_summaries(rows)}
    assert days["2026-10-16"]["n"] == 2 and days["2026-10-16"]["net"] == 600.0
    # Oct 19: 09:20 and 09:45 entries are hindsight; 09:50 and 13:00 count
    d19 = days["2026-10-19"]
    assert d19["n"] == 2 and d19["net"] == 1300.0
    assert d19["excluded"]["n"] == 2 and d19["excluded"]["net"] == 5300.0
    assert d19["shadow"]["n"] == 0
    tagged = [r for r in rows if r.get("hindsight_fill")]
    assert {r["trade_id"] for r in tagged} == {"RR-PX_B2-NIFTY-PE-0915", "RR-PX_EP010-NIFTY-CE-0944"}
    assert all(r["day"] == "2026-10-19" and "hindsight" in r["exclude_reason"] for r in tagged)
    split = _today_split(day_summaries(rows), "2026-10-19")
    assert split["desk_net_inr"] == 1300.0 and split["excluded_trades"] == 2


def test_board_owns_its_day_and_hindsight_applies_to_board_rows(tmp_path) -> None:
    from api.ui_feed import day_summaries, history_rows

    _setup(tmp_path)
    d19 = json.loads((tmp_path / "data" / "recon" / "research_rules" / "2026-10-19.json").read_text())["closed"]
    board = {"session_ist_date": "2026-10-19", "closed_trades": d19[:3]}  # mid-session board, 3 closed
    rows = history_rows(tmp_path, board, events={})
    days = {d["day"]: d for d in day_summaries(rows)}
    assert days["2026-10-19"]["n"] == 1 and days["2026-10-19"]["net"] == 2000.0
    assert days["2026-10-19"]["excluded"]["n"] == 2
    assert days["2026-10-16"]["net"] == 600.0


def test_other_days_are_not_hindsight_tagged(tmp_path) -> None:
    from api.ui_feed import tag_hindsight

    row = tag_hindsight({"trade_id": "x", "day": "2026-10-16", "entry_min": "09:16"})
    assert "hindsight_fill" not in row
    row = tag_hindsight({"trade_id": "x", "day": "2026-10-19", "entry_min": "09:47"})
    assert "hindsight_fill" not in row
