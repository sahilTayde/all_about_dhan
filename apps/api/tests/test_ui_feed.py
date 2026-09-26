import json

from api.ui_feed import attach_entry_spots

DAY = "2026-01-15"


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
    _write(tmp_path / "data" / "recon" / "ml_paper_model_logs.jsonl", [
        {"event": "OPEN", "trade_id": f"paper-X-NIFTY-{prior_ts}-PE", "limit": 90.0, "lots": 2, "lot_size": 50},
        {"event": "SKIP", "reason": "HOLD_MAJORITY"},
        {"event": "CLOSE", "trade_id": f"paper-X-NIFTY-{prior_ts}-PE", "book_id": "MIX-DEFAULT-BUY", "underlying": "NIFTY",
         "side": "PE", "strike": 20100, "pnl_points": -4.0, "gross_pnl_inr": -400.0, "charges_inr": 60.0,
         "pnl_inr": -460.0, "exit_reason": "STOP", "filled": True},
    ])
    rows = history_rows(tmp_path, board)
    assert [r["day"] for r in rows] == [DAY, DAY, "2026-01-14"]
    old = rows[-1]
    assert old["source"] == "model_log" and old["entry"] == 90.0 and old["exit"] == 86.0

    days = day_summaries(rows)
    assert days[0]["n"] == 1 and days[0]["net"] == 1000.0
    assert days[0]["by_book"]["MIX-ML-LOGIT"]["n"] == 1
    assert days[1] == {"day": "2026-01-14", "n": 1, "wins": 0, "gross": -400.0, "charges": 60.0, "net": -460.0,
                       "by_book": {"MIX-DEFAULT-BUY": {"n": 1, "wins": 0, "net": -460.0}},
                       "by_reason": {"STOP": {"n": 1, "net": -460.0}}}
    acct = account(board, days)
    assert acct["net_inr"] == 540.0 and acct["equity_inr"] == 500540.0 and acct["n_days"] == 2
    assert acct["funds_editable"] is False


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
