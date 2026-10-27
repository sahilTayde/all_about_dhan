import json
from pathlib import Path

from api.ui_feed import attach_entry_spots

DAY = "2026-01-15"
DESK_MODEL = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "deskModel.js"  # HealthStrip.jsx removed in the page redesign


def _row(hms: str, nifty: float, bank: float) -> str:
    stamp = f"{DAY}T{hms}+05:30"
    return json.dumps(
        {
            "as_of_ist": stamp,
            "underlyings": [
                {"underlying": "NIFTY", "index_ltp": nifty},
                {"underlying": "BANKNIFTY", "index_ltp": bank},
            ],
        }
    )


def test_spot_is_the_tape_print_at_entry_not_the_latest(tmp_path) -> None:
    tape = tmp_path / f"{DAY}.jsonl"
    tape.write_text(
        "\n".join([_row("09:30:00", 20000.0, 45000.0), _row("09:31:00", 20010.5, 45020.0), _row("15:29:00", 20500.0, 46000.0)])
        + "\n{half-written",
        encoding="utf-8",
    )
    blob = {
        "closed_trades": [
            {"underlying": "NIFTY", "opened_ist": f"{DAY}T09:31:40+05:30"},
            {"underlying": "BANKNIFTY", "opened_ist": f"{DAY}T09:30:05+05:30"},
            {"underlying": "NIFTY", "opened_ist": f"{DAY}T12:00:00+05:30"},  # tape gap > 180 s
            {"underlying": "NIFTY", "opened_ist": f"{DAY}T09:31:40+05:30", "spot_at_entry": 1.0},
        ],
        "open_trades": [{"underlying": "NIFTY", "opened_ist": f"{DAY}T09:29:00+05:30"}],  # before tape
    }
    attach_entry_spots(blob, tmp_path)
    closed = blob["closed_trades"]
    assert closed[0]["spot_at_entry"] == 20010.5
    assert closed[0]["spot_at_entry_src"] == "DUAL-TAPE"
    assert closed[1]["spot_at_entry"] == 45000.0
    assert "spot_at_entry" not in closed[2]
    assert closed[3]["spot_at_entry"] == 1.0
    assert "spot_at_entry" not in blob["open_trades"][0]

    with tape.open("a", encoding="utf-8") as fh:
        fh.write("\n" + _row("15:30:00", 20600.0, 46100.0) + "\n")
    late = {"closed_trades": [{"underlying": "NIFTY", "opened_ist": f"{DAY}T15:30:10+05:30"}]}
    attach_entry_spots(late, tmp_path)
    assert late["closed_trades"][0]["spot_at_entry"] == 20600.0


def test_missing_tape_dir_is_a_no_op(tmp_path) -> None:
    blob = {"closed_trades": [{"underlying": "NIFTY", "opened_ts": 1768449600}]}
    attach_entry_spots(blob, tmp_path / "nope")
    assert "spot_at_entry" not in blob["closed_trades"][0]


def _write(path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _board_trade(tid: str, book: str, net: float, opened: str) -> dict:
    return {"trade_id": tid, "book_id": book, "underlying": "NIFTY", "side": "CE", "atm_strike": 20000, "entry": 100.0,
            "exit": 105.0, "exit_reason": "TARGET", "gross_pnl_inr": net + 50, "charges_inr": 50.0,
            "realized_pnl_inr": net, "filled": True, "opened_ist": opened}


def test_history_merges_board_and_model_log_across_days(tmp_path) -> None:
    from api.ui_feed import account, day_summaries, history_rows

    today = f"{DAY}T10:00:00+05:30"
    board = {
        "capital_plan": {"desk_capital_inr": 500000.0},
        # same fill booked by two books: one unique fill for the day, two rows per book split
        "closed_trades": [_board_trade("a-DEFAULT", "MIX-DEFAULT-BUY", 1000.0, today),
                          _board_trade("a-LOGIT", "MIX-ML-LOGIT", 1000.0, today)],
    }
    prior_ts = 1768362000  # 2026-01-14 09:10 IST, earlier day that only the model log remembers
    tid = f"paper-X-NIFTY-{prior_ts}-PE"
    close = {"event": "CLOSE", "trade_id": tid, "book_id": "MIX-DEFAULT-BUY", "underlying": "NIFTY", "side": "PE",
             "strike": 20100, "pnl_points": -4.0, "gross_pnl_inr": -400.0, "charges_inr": 60.0, "pnl_inr": -460.0,
             "exit_reason": "STOP", "filled": True}
    replay_ts = 1768449000  # 2026-01-15 09:20 IST
    _write(tmp_path / "data" / "recon" / "ml_paper_model_logs.jsonl", [
        {"event": "OPEN", "trade_id": tid, "limit": 90.0, "lots": 2, "lot_size": 50, "ts_ist": "2026-01-14T09:10:05+05:30"},
        {"event": "SKIP", "reason": "HOLD_MAJORITY", "ts_ist": "2026-01-14T09:11:00+05:30"},
        {**close, "ts_ist": "2026-01-14T09:24:00+05:30"},
        # the same day replayed two days later, and a replay of the board's own day: neither may count
        {**close, "trade_id": f"paper-X-NIFTY-{prior_ts + 60}-PE", "ts_ist": "2026-01-16T20:00:00+05:30"},
        {**close, "trade_id": f"paper-X-NIFTY-{replay_ts}-CE", "ts_ist": "2026-01-15T09:30:00+05:30"},
        {**close, "trade_id": f"paper-X-NIFTY-{replay_ts + 60}-CE", "ts_ist": "2026-01-15T18:30:00+05:30"},
    ])
    rows = history_rows(tmp_path, board)
    assert [r["day"] for r in rows] == [DAY, DAY, "2026-01-14"]
    old = rows[-1]
    assert old["source"] == "model_log (live)" and old["entry"] == 90.0 and old["exit"] == 86.0

    days = day_summaries(rows)
    assert days[0]["n"] == 1 and days[0]["net"] == 1000.0
    assert days[0]["by_book"]["MIX-ML-LOGIT"]["n"] == 1
    assert days[1] == {"day": "2026-01-14", "shadow": {"n": 0, "net": 0.0, "by_book": {}}, "excluded": {"n": 0, "net": 0.0, "reasons": []}, "n": 1, "wins": 0, "gross": -400.0, "charges": 60.0, "net": -460.0,
                       "by_book": {"MIX-DEFAULT-BUY": {"n": 1, "wins": 0, "net": -460.0}},
                       "by_reason": {"STOP": {"n": 1, "gross": -400.0, "charges": 60.0, "net": -460.0}}}
    acct = account(board, days)
    assert acct["net_inr"] == 540.0 and acct["equity_inr"] == 500540.0 and acct["n_days"] == 2
    assert acct["funds_editable"] is True and acct["funds_added_inr"] == 0.0 and acct["min_capital_inr"] is None
    (tmp_path / "data" / "recon").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "recon" / "founder_account.json").write_text('{"funds_added_inr": 50000, "min_capital_inr": 300000}')
    funded = account(board, days, tmp_path)
    assert funded["funds_added_inr"] == 50000 and funded["min_capital_inr"] == 300000
    assert funded["equity_inr"] == 550540.0


def test_session_tape_age_prefers_today_v2_over_yesterday_board(tmp_path) -> None:
    from datetime import datetime

    from api.ui_feed import IST, MARKET_DATA_FRESH_S, health_rows, session_tape_age

    now = datetime(2026, 1, 15, 11, 0, tzinfo=IST)
    # Yesterday's board tick must not become "stale 18h" when today's V2 file exists.
    board = {"steps": {"NIFTY": {"span_ist": {"last": "2026-01-14T16:00:00+05:30"}}}}
    v2 = tmp_path / "data" / "tape" / "v2" / "2026-01-15"
    v2.mkdir(parents=True)
    tick = v2 / "depth_quotes.jsonl"
    tick.write_text("{}\n", encoding="utf-8")
    tick.touch()
    import os

    os.utime(tick, (now.timestamp() - 20, now.timestamp() - 20))
    age, src = session_tape_age(tmp_path, board, now)
    assert src == "v2 recorder"
    assert age is not None and age <= 25
    rows = health_rows(tmp_path, board, {"agents": [{"id": "paper-loop", "alive": True}]}, {}, now)
    data = next(r for r in rows if r["id"] == "data")
    assert data["tone"] == "green"
    assert "v2 recorder" in data["detail"]
    assert MARKET_DATA_FRESH_S == 120


def test_session_tape_90s_board_tick_is_green_not_slow(tmp_path) -> None:
    from datetime import datetime

    from api.ui_feed import IST, health_rows

    now = datetime(2026, 1, 15, 11, 0, tzinfo=IST)
    board = {"steps": {"NIFTY": {"span_ist": {"last": "2026-01-15T10:58:30+05:30"}}}}  # 90s
    rows = health_rows(tmp_path, board, {"agents": [{"id": "paper-loop", "alive": True}]}, {}, now)
    data = next(r for r in rows if r["id"] == "data")
    assert data["tone"] == "green"
    assert "fresh" in data["detail"]


def test_session_tape_ignores_yesterday_when_today_v2_dir_empty(tmp_path) -> None:
    from datetime import datetime

    from api.ui_feed import IST, session_tape_age

    now = datetime(2026, 1, 15, 11, 0, tzinfo=IST)
    (tmp_path / "data" / "tape" / "v2" / "2026-01-15").mkdir(parents=True)
    yesterday = tmp_path / "data" / "tape" / "v2" / "2026-01-14"
    yesterday.mkdir(parents=True)
    (yesterday / "depth_quotes.jsonl").write_text("{}\n", encoding="utf-8")
    board = {"steps": {"NIFTY": {"span_ist": {"last": "2026-01-14T16:00:00+05:30"}}}}
    age, src = session_tape_age(tmp_path, board, now)
    assert src == "v2 recorder"
    assert age is None


def test_health_strip_labels_paper_loop_and_v2_recorder() -> None:
    # #106 after the redesign: the paper heartbeat dot is "Paper loop" (never "Recorder"); the V2 Recorder
    # health row reaches the Ops page through feedAges, which lists every snap.health row by name.
    text = DESK_MODEL.read_text(encoding="utf-8")
    assert 'loop = pick("paper")' in text and '{ id: "loop", label: "Paper loop"' in text
    assert 'label: "Recorder"' not in text
    assert "for (const h of snap?.health || []) rows.push({ name: h.name" in text


def _touch_v2(tmp_path, now, name: str, age_s: int):
    import os

    from api.ui_feed import IST

    day = now.astimezone(IST).date().isoformat()
    v2 = tmp_path / "data" / "tape" / "v2" / day
    v2.mkdir(parents=True, exist_ok=True)
    path = v2 / name
    path.write_text("{}\n", encoding="utf-8")
    os.utime(path, (now.timestamp() - age_s, now.timestamp() - age_s))
    return path


def test_recorder_row_green_when_v2_tape_under_60s_even_if_paper_down(tmp_path) -> None:
    from datetime import datetime

    from api.ui_feed import IST, health_rows

    now = datetime(2026, 1, 15, 11, 0, tzinfo=IST)
    _touch_v2(tmp_path, now, "depth_quotes.jsonl", 20)
    rows = health_rows(tmp_path, {}, {"agents": [{"id": "paper-loop", "alive": False}]}, {}, now)
    by_id = {r["id"]: r for r in rows}
    assert by_id["paper"]["tone"] == "red"
    assert by_id["paper"]["name"] == "Paper loop"
    assert by_id["recorder"]["tone"] == "green"
    assert by_id["recorder"]["name"] == "Recorder"
    assert "v2 tape" in by_id["recorder"]["detail"]


def test_recorder_row_amber_under_300s_red_otherwise_grey_when_closed(tmp_path) -> None:
    from datetime import datetime

    from api.ui_feed import IST, health_rows

    now = datetime(2026, 1, 15, 11, 0, tzinfo=IST)
    fstatus = {"agents": [{"id": "paper-loop", "alive": True}]}
    _touch_v2(tmp_path, now, "recorder_status.json", 90)
    rows = health_rows(tmp_path, {}, fstatus, {}, now)
    rec = next(r for r in rows if r["id"] == "recorder")
    assert rec["tone"] == "amber"

    _touch_v2(tmp_path, now, "recorder_status.json", 400)
    rows = health_rows(tmp_path, {}, fstatus, {}, now)
    rec = next(r for r in rows if r["id"] == "recorder")
    assert rec["tone"] == "red"

    closed = datetime(2026, 1, 15, 16, 0, tzinfo=IST)
    rows = health_rows(tmp_path, {}, fstatus, {}, closed)
    rec = next(r for r in rows if r["id"] == "recorder")
    assert rec["tone"] == "grey"


def test_recorder_row_uses_newest_mtime_under_v2_day(tmp_path) -> None:
    from datetime import datetime

    from api.ui_feed import IST, health_rows, session_tape_age

    now = datetime(2026, 1, 15, 11, 0, tzinfo=IST)
    _touch_v2(tmp_path, now, "depth_quotes.jsonl", 400)
    _touch_v2(tmp_path, now, "recorder_status.json", 15)
    age, src = session_tape_age(tmp_path, {}, now)
    assert src == "v2 recorder"
    assert age is not None and age <= 20
    rec = next(r for r in health_rows(tmp_path, {}, {}, {}, now) if r["id"] == "recorder")
    assert rec["tone"] == "green"


def test_session_tape_falls_back_to_today_dual_tape(tmp_path) -> None:
    from datetime import datetime
    import os

    from api.ui_feed import IST, session_tape_age

    now = datetime(2026, 1, 15, 11, 0, tzinfo=IST)
    dual = tmp_path / "data" / "recon" / "paper_watch" / "DUAL-TAPE" / "2026-01-15.jsonl"
    dual.parent.mkdir(parents=True)
    dual.write_text("{}\n", encoding="utf-8")
    os.utime(dual, (now.timestamp() - 40, now.timestamp() - 40))
    age, src = session_tape_age(tmp_path, {}, now)
    assert src == "dual-tape"
    assert age is not None and 35 <= age <= 45


def test_stale_tape_in_market_hours_is_red_and_alerts(tmp_path) -> None:
    from datetime import datetime

    from api.ui_feed import IST, alert_list, health_rows

    now = datetime(2026, 1, 15, 11, 0, tzinfo=IST)  # Thursday, market open
    board = {"steps": {"NIFTY": {"span_ist": {"last": "2026-01-15T10:50:00+05:30"}}},
             "open_trades": [{"trade_id": "t1", "underlying": "NIFTY", "side": "CE", "opened_ist": "2026-01-15T10:30:00+05:30"}]}
    fstatus = {"agents": [{"id": "paper-loop", "alive": True}], "started_at_ist": "2026-01-15T10:40:00+05:30"}
    rows = health_rows(tmp_path, board, fstatus, {}, now)
    tone = {r["id"]: r["tone"] for r in rows}
    assert tone["data"] == "red" and tone["paper"] == "green" and tone["db"] == "grey"
    alerts = alert_list(board, rows, {}, [], fstatus, now)
    titles = [a["title"] for a in alerts]
    assert "Stale market data" in titles and "Restart during an open trade" in titles
    assert all(a["severity"] == "CRITICAL" for a in alerts)


def test_trace_greys_steps_without_records(tmp_path) -> None:
    from api.ui_feed import trade_trace

    board = {"closed_trades": [{**_board_trade("t9", "MIX-DEFAULT-BUY", 10.0, f"{DAY}T10:00:00+05:30"),
                                "execution": "refused", "strike_source": "ITM_100", "justification": "x; why_now=CE bin; y"}]}
    _write(tmp_path / "data" / "recon" / "ml_paper_dashboard.json", [])
    (tmp_path / "data" / "recon" / "ml_paper_dashboard.json").write_text(json.dumps(board), encoding="utf-8")
    trace = trade_trace(tmp_path, "t9")
    status = {s["id"]: s["status"] for s in trace["steps"]}
    assert [s["id"] for s in trace["steps"]] == ["data", "analysts", "boss", "risk", "desk", "broker", "fill"]
    assert status["risk"] == "NO_DATA" and status["data"] == "NO_DATA" and status["analysts"] == "NO_DATA"
    assert status["broker"] == "PAPER" and status["fill"] == "OK"
    assert trace["steps"][2]["why"] == "CE bin"
    assert trade_trace(tmp_path, "missing")["ok"] is False


def test_mtm_halt_file_is_a_critical_alert_and_red_row(tmp_path) -> None:
    from datetime import datetime

    from api.ui_feed import IST, build_snapshot

    halt = tmp_path / "data" / "desk" / "live_loop" / "mtm_halt.json"
    halt.parent.mkdir(parents=True)
    halt.write_text(json.dumps({"session": "2026-01-15", "halt_ts": 1768455000, "reason": "stop path failed", "kinds": ["mtm"],
                                "forced_closes": [], "entries_blocked": True}), encoding="utf-8")
    now = datetime(2026, 1, 15, 11, 0, tzinfo=IST)
    snap = build_snapshot(tmp_path, now=now, fstatus={})
    assert snap["risk_halt"]["reason"] == "stop path failed"
    assert {r["id"]: r["tone"] for r in snap["health"]}["risk"] == "red"
    assert snap["alerts"][0]["title"] == "Risk halt — new entries blocked"

    halt.write_text("{not json", encoding="utf-8")
    assert build_snapshot(tmp_path, now=now, fstatus={})["risk_halt"]["active"] is True
    halt.write_text(json.dumps({"session": "2026-01-14", "halt_ts": 1}), encoding="utf-8")
    assert build_snapshot(tmp_path, now=now, fstatus={})["risk_halt"] is None


def test_new_rows_streams_from_offset_with_needles_and_budget(tmp_path) -> None:
    from api.ui_feed import new_rows

    path = tmp_path / "log.jsonl"
    _write(path, [{"event": "SKIP", "i": i} for i in range(5000)] + [{"event": "CLOSE", "i": -1}])
    rows, reset, done = new_rows(path, (b'"event": "CLOSE"',), budget_s=0.0)
    assert reset and not done and rows == []  # budget spent after the first 2048 lines
    while not done:
        more, reset, done = new_rows(path, (b'"event": "CLOSE"',), budget_s=0.0)
        assert not reset
        rows += more
    assert rows == [{"event": "CLOSE", "i": -1}]
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"event": "CLOSE", "i": 7}) + "\n" + '{"event": "CLOSE", "i"')  # half-written tail
    assert new_rows(path, (b'"event": "CLOSE"',))[0] == [{"event": "CLOSE", "i": 7}]


def test_alert_ids_change_per_episode_and_news_uses_item_time(tmp_path) -> None:
    from datetime import datetime

    from api.ui_feed import IST, alert_list, health_rows, latest_news_ts

    now = datetime(2026, 1, 15, 11, 0, tzinfo=IST)
    ids = []
    for last in ("2026-01-15T10:50:00+05:30", "2026-01-15T10:40:00+05:30"):
        board = {"steps": {"NIFTY": {"span_ist": {"last": last}}}}
        rows = health_rows(tmp_path, board, {"agents": [{"id": "paper-loop", "alive": True}]}, {}, now)
        ids.append(next(a["id"] for a in alert_list(board, rows, {}, [], {}, now) if a["title"] == "Stale market data"))
    assert ids[0] != ids[1]

    folder = tmp_path / "data" / "desk_intel" / "signals"
    folder.mkdir(parents=True)
    (folder / "x.json").write_text(json.dumps({"news": [{"headline": "a", "time_ist": "2026-01-15T08:00:00+05:30"},
                                                        {"headline": "b", "time_ist": "2026-01-15T09:30:00+05:30"}]}))
    (tmp_path / "data" / "desk_intel" / ".gitkeep").write_text("")
    assert latest_news_ts(tmp_path) == int(datetime(2026, 1, 15, 9, 30, tzinfo=IST).timestamp())


def test_history_complete_flag_and_non_blocking_warmer(tmp_path) -> None:
    import threading
    import time

    from api import ui_feed
    from api.ui_feed import build_snapshot, start_history_warmer

    prior_ts = 1768362000
    rows = [{"event": "SKIP", "i": i, "pad": "x" * 200} for i in range(30000)]
    rows.append({"event": "CLOSE", "trade_id": f"paper-X-NIFTY-{prior_ts}-PE", "book_id": "MIX-DEFAULT-BUY", "underlying": "NIFTY",
                 "side": "PE", "pnl_points": -4.0, "gross_pnl_inr": -400.0, "charges_inr": 60.0, "pnl_inr": -460.0,
                 "exit_reason": "STOP", "filled": True, "ts_ist": "2026-01-14T09:24:00+05:30"})
    _write(tmp_path / "data" / "recon" / "ml_paper_model_logs.jsonl", rows)

    # A budgeted snapshot that has not read the whole log says so, and counts no partial day.
    first = build_snapshot(tmp_path, fstatus={}, budget_s=0.0)
    assert first["history_complete"] is False and first["days"] == []

    # While the warmer holds the index, a snapshot returns at once with the flag still false.
    with ui_feed._EVENTS_LOCK:
        t0 = time.monotonic()
        held = build_snapshot(tmp_path, fstatus={}, budget_s=ui_feed.SNAPSHOT_BUDGET_S)
        assert time.monotonic() - t0 < 1.0
        assert held["history_complete"] is False

    warmer = start_history_warmer(tmp_path)
    assert isinstance(warmer, threading.Thread)
    warmer.join(10)
    done = build_snapshot(tmp_path, fstatus={}, budget_s=ui_feed.SNAPSHOT_BUDGET_S)
    assert done["history_complete"] is True
    assert [(d["day"], d["net"]) for d in done["days"]] == [("2026-01-14", -460.0)]
    assert done["account"]["net_inr"] == -460.0


def test_decision_journal_on_snapshot_and_trace(tmp_path) -> None:
    from desk_ml.decision_journal import DecisionJournal, make_row

    ts = 1768452300  # 2026-01-15 10:15 IST-ish; day comes from ts_ist
    board = {"session_ist_date": DAY, "closed_trades": [_board_trade("t-n", "MIX-DEFAULT-BUY", 10.0, f"{DAY}T10:00:00+05:30")]}
    (tmp_path / "data" / "recon").mkdir(parents=True)
    (tmp_path / "data" / "recon" / "ml_paper_dashboard.json").write_text(json.dumps(board), encoding="utf-8")
    journal = DecisionJournal(tmp_path)
    journal.append(
        make_row(
            ts=f"{DAY}T10:00:00+05:30",
            underlying="NIFTY",
            candidate_id="t-n",
            stage="overlay",
            actor="Overlay",
            decision="pass",
            reason="Market TREND",
            inputs={"day_type": "TREND", "vix": 12.4, "premium": 100, "sl": 94, "target": 106},
            trade_id="t-n",
        )
    )
    from api.ui_feed import build_snapshot, decision_journal, trade_trace

    snap = build_snapshot(tmp_path, fstatus={})
    assert snap["decision_journal"]
    assert snap["board"]["decision_journal"][0]["stage"] == "overlay"
    assert "MIX-" not in json.dumps(snap["decision_journal"])
    blob = decision_journal(tmp_path, day=DAY)
    assert blob["n"] == 1 and blob["orders"] == "REFUSED"
    trace = trade_trace(tmp_path, "t-n")
    assert trace["journal"][0]["candidate_id"] == "t-n"
    assert trace["journal"][0]["inputs"]["day_type"] == "TREND"


def test_snapshot_stamps_explainer_and_shadow_panel(tmp_path) -> None:
    from desk_ml.decision_journal import DecisionJournal, make_row
    from desk_ml.llm_shadow_compare import COMPARE_REL

    board = {"session_ist_date": DAY, "open_trades": [_board_trade("t-n", "MIX-DEFAULT-BUY", 10.0, f"{DAY}T10:00:00+05:30")]}
    (tmp_path / "data" / "recon").mkdir(parents=True)
    (tmp_path / "data" / "recon" / "ml_paper_dashboard.json").write_text(json.dumps(board), encoding="utf-8")
    journal = DecisionJournal(tmp_path)
    journal.append(
        make_row(
            ts=f"{DAY}T10:00:00+05:30",
            underlying="NIFTY",
            candidate_id="t-n",
            stage="llm_explain",
            actor="LLM judge",
            decision="pass",
            reason="Call premium is following a rising index.",
            inputs={"market_type": "trend up", "side": "CE", "explanation": "Call premium is following a rising index."},
            trade_id="t-n",
        )
    )
    cum = tmp_path / "data" / "recon" / "llm_shadow_compare"
    cum.mkdir(parents=True)
    (tmp_path / COMPARE_REL / "cumulative.json").write_text(
        json.dumps(
            {
                "schema": "llm-shadow-compare-v1",
                "r3_net": 200.0,
                "random_mean": 50.0,
                "r3_minus_random": 150.0,
                "n_days": 1,
                "days": [{"day": DAY, "r3_net": 200.0, "random_mean": 50.0}],
                "trade": False,
                "promote": False,
            }
        ),
        encoding="utf-8",
    )
    from api.ui_feed import build_snapshot

    snap = build_snapshot(tmp_path, fstatus={})
    live = snap["board"]["open_trades"][0]
    assert live["llm_explanation"] == "Call premium is following a rising index."
    assert live["market_type"] == "trend up"
    assert live["entry"] == 100.0
    assert live["realized_pnl_inr"] == 10.0
    assert snap["llm_shadow_compare"]["r3_net"] == 200.0
    assert snap["llm_shadow_compare"]["trade"] is False
    assert snap["llm_shadow_compare"]["r4"]["status"] == "MISSING_PROMPT"
    assert "cd147c1a" in str(snap["llm_shadow_compare"]["r4"].get("expected_sha256_prefix"))
    assert "TREND_UP" not in json.dumps(snap["board"]["open_trades"])
