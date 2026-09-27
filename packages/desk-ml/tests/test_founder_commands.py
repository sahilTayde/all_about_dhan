"""Founder emergency controls (roadmap step 14) replayed on the synthetic NIFTY session.

Every command applies from its own timestamp, entries fail closed and founder exits are never
refused. Baseline (no commands): 12 trades / +69,364.32 (docs: reliability spec §1).
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

import desk_ml.paper_scalp as ps
from desk_ml.event_parity import compare_boards, fixture_replay_kwargs, load_fixture
from desk_ml.founder_commands import append_command, load_book, log_path, make_row, read_commands
from desk_ml.founder_commands import book as fcb
from desk_ml.founder_session import save_founder_book

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "synthetic_session_nifty.json"
DAY = "2026-09-10"
CUT_ID = "paper-MIX-DEFAULT-BUY-NIFTY-1789028100-CE"  # 13:45:00 -> 14:28:40 CANCEL_STALL in the baseline
T1_ID = "paper-MIX-DEFAULT-BUY-NIFTY-1789015280-PE"  # 10:11:20 -> 10:17:40 TARGET in the baseline


def at(hhmm: str, sec: int = 0) -> int:
    h, m = (int(x) for x in hhmm.split(":"))
    return int(datetime(2026, 9, 10, h, m, sec, tzinfo=fcb.IST).timestamp())


def cmd(kind: str, hhmm: str, **args):
    return make_row(kind, args, actor="test", reason=f"test {kind}", ts=at(hhmm), command_id=f"{kind}-{hhmm.replace(':', '')}")


def ist(ts) -> str:
    return datetime.fromtimestamp(int(ts), fcb.IST).strftime("%H:%M:%S")


@pytest.fixture(scope="module")
def fx():
    return load_fixture(FIXTURE)


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, fx):
    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})
    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: (int(fx["lot_size"]), "fixture"))
    monkeypatch.delenv(ps.USE_EVENT_BUS_ENV, raising=False)
    monkeypatch.setenv("AAD_FOUNDER_SPOOL_DIR", "/nonexistent-spool-for-tests")


def replay(fx, root, commands=None, *, until=None, founder_file=True, write=False, **kw):
    kwargs = fixture_replay_kwargs(fx, root)
    if not founder_file:
        save_founder_book([], root=root)
    if until is not None:
        kwargs["triples_by_und"] = {"NIFTY": [t for t in fx["triples"] if t.ts <= at(until)]}
    return ps.replay_paper_scalp(**kwargs, write=write, founder_commands=commands, **kw)


@pytest.fixture(scope="module")
def baseline(fx, tmp_path_factory):
    mp = pytest.MonkeyPatch()
    mp.setattr(ps, "load_index_closes", lambda u, root=None: {})
    mp.setattr(ps, "resolve_lot_size", lambda und, root=None: (int(fx["lot_size"]), "fixture"))
    try:
        return replay(fx, tmp_path_factory.mktemp("base"))["closed_trades"]
    finally:
        mp.undo()


def by_id(rows):
    return {r["trade_id"]: r for r in rows}


def result(board, cid):
    return next(r for r in board["founder_controls"]["results"] if r["id"] == cid)


def opened_between(rows, a, b):
    return [r for r in rows if a <= int(r["opened_ts"]) < b]


def assert_unchanged_before(rows, baseline, ts):
    before = {k: v for k, v in by_id(baseline).items() if int(v["closed_ts"]) < ts}
    assert before, "test needs baseline trades before the command"
    got = by_id(rows)
    for tid, row in before.items():
        assert got[tid] == row, f"{tid} changed although it closed before the command"


# ------------------------------------------------------------------ parity


def test_no_commands_is_exact(fx, tmp_path, baseline):
    assert len(baseline) == 12 and round(sum(r["realized_pnl_inr"] for r in baseline), 2) == 69364.32
    board = replay(fx, tmp_path)  # no log file under root
    assert board["closed_trades"] == baseline and "founder_controls" not in board
    assert replay(fx, tmp_path, [])["closed_trades"] == baseline


def test_commands_after_the_session_change_nothing(fx, tmp_path, baseline):
    later = [make_row("KILL", {}, actor="t", reason="t", ts=at("15:30") + 86400, command_id="k1")]
    board = replay(fx, tmp_path, later)
    assert board["closed_trades"] == baseline
    assert result(board, "k1")["status"] == "pending"


# -------------------------------------------------------------- each command


def test_stop_then_start(fx, tmp_path, baseline):
    board = replay(fx, tmp_path, [cmd("STOP", "11:00"), cmd("START", "12:20")])
    rows = board["closed_trades"]
    assert_unchanged_before(rows, baseline, at("11:00"))
    assert not opened_between(rows, at("11:00"), at("12:20"))
    assert opened_between(rows, at("12:20"), at("15:30")), "START must let entries resume"
    assert board["skip_reason_counts"].get(fcb.STOPPED)
    assert {result(board, c)["status"] for c in ("STOP-1100", "START-1220")} == {"applied"}


def test_pause_blocks_entries_for_n_minutes(fx, tmp_path, baseline):
    board = replay(fx, tmp_path, [cmd("PAUSE", "12:20", minutes=30)])
    rows = board["closed_trades"]
    assert_unchanged_before(rows, baseline, at("12:20"))
    assert not opened_between(rows, at("12:20"), at("12:50"))
    assert opened_between(rows, at("12:50"), at("15:30"))
    assert board["skip_reason_counts"].get(fcb.PAUSED)


def test_blocked_windows(fx, tmp_path, baseline):
    wins = [{"start": "09:15", "end": "10:05"}, {"start": "13:00", "end": "14:00"}]
    board = replay(fx, tmp_path, [cmd("BLOCK_WINDOWS", "09:00", windows=wins)])
    rows = board["closed_trades"]
    assert rows and not opened_between(rows, at("09:15"), at("10:05")) and not opened_between(rows, at("13:00"), at("14:00"))
    assert board["skip_reason_counts"].get(fcb.BLOCKED_WINDOW)
    assert board["founder_controls"]["state"]["blocked_windows"] == wins


def test_cut_loss_exits_that_position_at_market(fx, tmp_path, baseline):
    board = replay(fx, tmp_path, [cmd("CUT_LOSS", "14:00", trade_id=CUT_ID)])
    rows = by_id(board["closed_trades"])
    row = rows[CUT_ID]
    assert row["exit_reason"] == fcb.CUT_LOSS_REASON and ist(row["closed_ts"]) == "14:00:00"
    # at market: the held strike's print on that tick, else its last print (the engine's MTM rule)
    prints = [
        q for t in fx["triples"] if at("13:45") <= t.ts <= at("14:00")
        for q in [ps.quote_for_side(t, "CE", strike=row["atm_strike"], itm_only=True)[0]] if q is not None
    ]
    assert prints and row["exit"] == round(prints[-1], 4)
    assert_unchanged_before(board["closed_trades"], baseline, at("13:45"))
    res = result(board, "CUT_LOSS-1400")
    assert res["status"] == "applied" and res["trade_id"] == CUT_ID and res["applied_ts"] == at("14:00")


def test_cut_loss_on_a_closed_trade_is_rejected_with_reason(fx, tmp_path, baseline):
    board = replay(fx, tmp_path, [cmd("CUT_LOSS", "11:00", trade_id=T1_ID)])  # closed at 10:17
    assert board["closed_trades"] == baseline
    res = result(board, "CUT_LOSS-1100")
    assert res["status"] == "rejected" and res["status_reason"].startswith("TRADE_NOT_OPEN")


def test_go_for_t2_holds_past_the_first_target(fx, tmp_path, baseline):
    assert by_id(baseline)[T1_ID]["exit_reason"] == "TARGET"
    board = replay(fx, tmp_path, [cmd("GO_T2", "10:12", trade_id=T1_ID)])
    row = by_id(board["closed_trades"])[T1_ID]
    assert row["target_step"] >= 1, "first target must lock + extend instead of flattening"
    assert row["target"] > by_id(baseline)[T1_ID]["target"]
    assert_unchanged_before(board["closed_trades"], baseline, at("10:11"))
    assert result(board, "GO_T2-1012")["status"] == "applied"


def test_change_lots_for_next_trades(fx, tmp_path, baseline):
    board = replay(fx, tmp_path, [cmd("SET_LOTS", "12:00", lots=10)])
    rows = board["closed_trades"]
    assert_unchanged_before(rows, baseline, at("12:00"))
    later = [r for r in rows if r["filled"] and int(r["opened_ts"]) >= at("12:00")]
    assert later and {r["lots"] for r in later} == {10}
    assert {r["lots"] for r in rows if int(r["opened_ts"]) < at("12:00")} == {25}


def _risk_limits(root, max_lots):
    src = (Path(__file__).resolve().parents[3] / "config" / "risk_limits.yaml").read_text(encoding="utf-8")
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "risk_limits.yaml").write_text(
        src.replace("  paper:\n    max_lots_per_trade: 25", f"  paper:\n    max_lots_per_trade: {max_lots}"), encoding="utf-8"
    )


def test_lots_override_is_capped_by_the_risk_limits_in_the_engine(fx, tmp_path):
    """A hand-written row that bypasses the API still cannot exceed the risk limits' lots cap."""
    _risk_limits(tmp_path, 22)
    rows = replay(fx, tmp_path, [cmd("SET_LOTS", "09:00", lots=40)])["closed_trades"]
    assert rows and {r["lots"] for r in rows if r["filled"]} == {22}
    _risk_limits(tmp_path, 25)  # the repo's paper cap
    rows = replay(fx, tmp_path, [cmd("SET_LOTS", "09:00", lots=40)])["closed_trades"]
    assert {r["lots"] for r in rows if r["filled"]} == {25}


def test_unreadable_risk_limits_let_a_lots_override_only_lower(fx, tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "risk_limits.yaml").write_text("mode: [broken", encoding="utf-8")
    up = replay(fx, tmp_path, [cmd("SET_LOTS", "09:00", lots=40)])["closed_trades"]
    assert up and {r["lots"] for r in up if r["filled"]} == {ps.PAPER_TARGET_LOTS}
    down = replay(fx, tmp_path, [cmd("SET_LOTS", "09:00", lots=10)])["closed_trades"]
    assert {r["lots"] for r in down if r["filled"]} == {10}


def test_kill_switch_flattens_open_positions_and_blocks_until_rearm(fx, tmp_path, baseline):
    board = replay(fx, tmp_path, [cmd("KILL", "13:50")])
    rows = board["closed_trades"]
    killed = by_id(rows)[CUT_ID]
    assert killed["exit_reason"] == fcb.KILL_REASON and ist(killed["closed_ts"]) == "13:50:00"
    assert not opened_between(rows, at("13:50"), at("15:30"))
    assert board["skip_reason_counts"].get(fcb.KILLED)
    res = result(board, "KILL-1350")
    assert res["status"] == "applied" and res["flattened"] == [CUT_ID]
    assert board["founder_controls"]["state"]["killed"] is True

    rearmed = replay(fx, tmp_path, [cmd("KILL", "13:50"), cmd("REARM", "14:40")])["closed_trades"]
    assert not opened_between(rearmed, at("13:50"), at("14:40"))
    assert opened_between(rearmed, at("14:40"), at("15:30")), "re-arm must let entries resume"


def test_start_does_not_rearm_the_kill_switch(fx, tmp_path):
    rows = replay(fx, tmp_path, [cmd("KILL", "13:50"), cmd("START", "14:00")])["closed_trades"]
    assert not opened_between(rows, at("13:50"), at("15:30"))


def test_per_index_disable_and_enable(fx, tmp_path, baseline):
    off = replay(fx, tmp_path, [cmd("INDEX", "12:00", underlying="NIFTY", enabled=False)])
    assert not opened_between(off["closed_trades"], at("12:00"), at("15:30"))
    assert off["skip_reason_counts"].get(fcb.INDEX_DISABLED)
    # the older START/STOP file says STOP NIFTY; an explicit founder enable outranks it
    assert replay(fx, tmp_path, founder_file=False)["closed_trades"] == []
    on = replay(fx, tmp_path, [cmd("INDEX", "09:00", underlying="NIFTY", enabled=True)], founder_file=False)
    assert on["closed_trades"] == baseline
    other = replay(fx, tmp_path, [cmd("INDEX", "09:00", underlying="FINNIFTY", enabled=False)])
    assert other["closed_trades"] == baseline
    assert other["founder_controls"]["state"]["index_enabled"] == {"FINNIFTY": False}


def test_min_capital_and_add_funds(fx, tmp_path, baseline):
    blocked = replay(fx, tmp_path, [cmd("MIN_CAPITAL", "09:00", amount_inr=10_000_000)])
    assert blocked["closed_trades"] == [] and blocked["skip_reason_counts"].get(fcb.BELOW_MIN_CAPITAL)
    funded = replay(fx, tmp_path, [cmd("MIN_CAPITAL", "09:00", amount_inr=10_000_000), cmd("ADD_FUNDS", "12:00", amount_inr=10_000_000)])
    rows = funded["closed_trades"]
    assert not opened_between(rows, at("09:00"), at("12:00")) and opened_between(rows, at("12:00"), at("15:30"))
    assert funded["founder_controls"]["state"]["funds_added_inr"] == 10_000_000


def test_replay_loads_a_commands_file(fx, tmp_path, baseline):
    for row in (cmd("STOP", "11:00"), cmd("START", "12:20")):
        append_command(tmp_path / "saved", row)
    path = log_path(tmp_path / "saved")
    from_file = replay(fx, tmp_path, path)["closed_trades"]
    assert from_file == replay(fx, tmp_path, [cmd("STOP", "11:00"), cmd("START", "12:20")])["closed_trades"]
    assert from_file != baseline
    assert replay(fx, tmp_path, path)["closed_trades"] == from_file, "replay must be deterministic"


def test_default_reads_the_root_log(fx, tmp_path, baseline):
    append_command(tmp_path, cmd("KILL", "13:50"))
    rows = replay(fx, tmp_path)["closed_trades"]
    assert by_id(rows)[CUT_ID]["exit_reason"] == fcb.KILL_REASON


# ------------------------------------------------------------- restarts


def test_restart_mid_pause(fx, tmp_path, baseline):
    """Live cycles re-replay from 09:15. A restart throws away every object and rereads the log."""
    append_command(tmp_path, cmd("PAUSE", "12:20", minutes=30))
    cycle1 = replay(fx, tmp_path, until="12:35")  # process 1, mid-pause
    assert not opened_between(cycle1["closed_trades"], at("12:20"), at("12:50"))
    assert result(cycle1, "PAUSE-1220")["status"] == "applied"
    assert cycle1["founder_controls"]["state"]["paused_until_ist"].endswith("12:50:00+05:30")

    assert read_commands(tmp_path).rows[0]["id"] == "PAUSE-1220"  # still on disk for process 2
    cycle2 = replay(fx, tmp_path)  # process 2 after the restart, full day
    rows2 = by_id(cycle2["closed_trades"])
    for row in cycle1["closed_trades"]:
        assert rows2[row["trade_id"]] == row, "a restart must not rewrite trades booked before it"
    assert not opened_between(cycle2["closed_trades"], at("12:20"), at("12:50"))
    assert opened_between(cycle2["closed_trades"], at("12:50"), at("15:30"))
    assert cycle2["founder_controls"]["state"]["paused_until_ist"] is None


# ------------------------------------------------------- fail directions


def test_corrupt_log_fails_closed_for_entries_and_open_for_exits(fx, tmp_path, baseline):
    path = log_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    good_then_bad = [
        json.dumps(cmd("INDEX", "13:50", underlying="SENSEX", enabled=True)),
        '{"id": "broken", "kind": "STO',
        json.dumps(cmd("CUT_LOSS", "14:00", trade_id=CUT_ID)),
    ]
    path.write_text("\n".join(good_then_bad) + "\n", encoding="utf-8")
    board = replay(fx, tmp_path)
    rows = board["closed_trades"]
    assert by_id(rows)[CUT_ID]["exit_reason"] == fcb.CUT_LOSS_REASON, "exits still apply"
    assert not opened_between(rows, at("13:50"), at("15:30")), "entries blocked after the last good line"
    assert_unchanged_before(rows, baseline, at("13:45"))
    assert board["skip_reason_counts"].get(fcb.UNREADABLE)
    assert board["founder_controls"]["problems"] == ["log line 2: not JSON"]


def _live_cycles(fx, root, cycles, appends):
    """The live loop: before each cycle, append due log lines; then re-replay the day up to that time (write=True)."""
    path = log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    boards = {}
    for hhmm in cycles:
        for due, line in [a for a in appends if a[0] <= hhmm]:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        appends = [a for a in appends if a[0] > hhmm]
        boards[hhmm] = replay(fx, root, until=hhmm, write=True)
    return boards


@pytest.mark.parametrize("earlier_good_command", [True, False])
def test_live_loop_keeps_trades_booked_before_a_corrupt_line_appeared(fx, tmp_path, baseline, earlier_good_command):
    """Sep-25 finding: a line going bad at 12:30 must not erase trades the loop booked before it saw it."""
    good = [("10:00", json.dumps(cmd("INDEX", "10:00", underlying="SENSEX", enabled=True)))] if earlier_good_command else []
    appends = good + [("12:30", '{"id": "broken", "kind": "STO')]
    boards = _live_cycles(fx, tmp_path, ["12:20", "12:40", "13:30", "15:30"], appends)
    booked = boards["12:20"]["closed_trades"]
    assert by_id(booked) == {k: v for k, v in by_id(baseline).items() if int(v["closed_ts"]) <= at("12:20")}
    assert len(booked) == 4
    for hhmm in ("12:40", "13:30", "15:30"):
        rows = by_id(boards[hhmm]["closed_trades"])
        for row in booked:
            assert rows.get(row["trade_id"]) == row, f"{row['trade_id']} vanished or changed in the {hhmm} cycle"
    first_seen = json.loads((tmp_path / "data" / "recon" / "founder_controls_problems.json").read_text())
    seen_at = max(t.ts for t in fx["triples"] if t.ts <= at("12:40"))
    assert list(first_seen.values()) == [seen_at]  # tape time of the first cycle that saw it
    final = boards["15:30"]
    assert not opened_between(final["closed_trades"], seen_at, at("15:30"))
    assert opened_between(final["closed_trades"], at("12:20"), seen_at), "entries before first sight stay"
    assert final["founder_controls"]["entries_blocked_from_ts"] == seen_at
    # a later offline replay of the same root reads the first-seen record: same board as the live loop
    assert replay(fx, tmp_path)["closed_trades"] == final["closed_trades"]


def test_first_seen_falls_back_to_the_last_good_line_when_it_cannot_be_stored(tmp_path, monkeypatch):
    import desk_ml.founder_commands.log as fl

    path = log_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(cmd("STOP", "10:00")) + "\nnot json\n", encoding="utf-8")
    res = read_commands(tmp_path)
    monkeypatch.setattr(fl, "_atomic_json", lambda *a, **k: False)
    assert fl.anchor_first_seen(tmp_path, res, as_of=at("12:40"), record=True) == at("10:00")
    monkeypatch.undo()
    assert fl.anchor_first_seen(tmp_path, res, as_of=at("12:40"), record=True) == at("12:40")
    assert fl.anchor_first_seen(tmp_path, res, as_of=at("14:00"), record=True) == at("12:40"), "first sight is kept"
    fl.first_seen_path(tmp_path).write_text("[1, 2]", encoding="utf-8")  # untrusted record: never later
    assert fl.anchor_first_seen(tmp_path, res, as_of=at("14:00"), record=True) == at("10:00")


def test_deeply_nested_line_is_a_problem_not_a_crash(fx, tmp_path, baseline):
    path = log_path(tmp_path)
    path.parent.mkdir(parents=True)
    deep = "[" * 200_000 + "]" * 200_000
    path.write_text(json.dumps(cmd("CUT_LOSS", "14:00", trade_id=CUT_ID)) + "\n" + deep + "\n", encoding="utf-8")
    res = read_commands(tmp_path)
    assert [r["id"] for r in res.rows] == ["CUT_LOSS-1400"] and res.problems == ["log line 2: not JSON"]
    board = replay(fx, tmp_path)
    assert by_id(board["closed_trades"])[CUT_ID]["exit_reason"] == fcb.CUT_LOSS_REASON, "exits still run"


def test_cut_loss_row_without_session_does_not_crash_the_report(fx, tmp_path, baseline):
    row = cmd("CUT_LOSS", "11:00", trade_id=T1_ID)  # T1 closed at 10:17: rejected at report time
    del row["session"]
    board = replay(fx, tmp_path, [row])
    assert board["closed_trades"] == baseline
    assert result(board, "CUT_LOSS-1100")["status"] == "rejected"


def test_unreadable_log_blocks_every_entry(fx, tmp_path):
    log_path(tmp_path).mkdir(parents=True)  # a directory where the log should be
    board = replay(fx, tmp_path)
    assert board["closed_trades"] == [] and board["skip_reason_counts"].get(fcb.UNREADABLE)


def test_invalid_row_blocks_entries_from_the_start(fx, tmp_path):
    bad = {**cmd("SET_LOTS", "09:00", lots=10), "args": {"lots": -3}}
    assert replay(fx, tmp_path, [bad])["closed_trades"] == []


def test_unfinished_last_line_is_ignored(fx, tmp_path, baseline):
    path = log_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cmd("KILL", "13:50"))[:25], encoding="utf-8")  # crash mid-write, never acked
    board = replay(fx, tmp_path)
    assert board["closed_trades"] == baseline and "founder_controls" not in board


def test_cut_loss_books_even_when_the_normal_close_raises(fx, tmp_path, baseline, monkeypatch):
    real = ps._close

    def disk_full(engine, pos, *, reason, **kw):
        if reason.startswith("FOUNDER_"):
            raise OSError(28, "No space left on device")
        return real(engine, pos, reason=reason, **kw)

    monkeypatch.setattr(ps, "_close", disk_full)
    board = replay(fx, tmp_path, [cmd("CUT_LOSS", "14:00", trade_id=CUT_ID)])
    row = by_id(board["closed_trades"])[CUT_ID]
    assert row["exit_reason"] == fcb.CUT_LOSS_REASON and ist(row["closed_ts"]) == "14:00:00"
    assert "OSError" in row["founder_fallback"]
    assert result(board, "CUT_LOSS-1400")["status"] == "applied"


def test_a_broken_command_book_never_blocks_engine_exits(fx, tmp_path, baseline, monkeypatch):
    monkeypatch.setattr(fcb.CommandBook, "manage", lambda *a, **k: 1 / 0)
    board = replay(fx, tmp_path, [cmd("START", "09:00")])
    assert board["closed_trades"] == baseline


# ---------------------------------------------------------- event path


def test_event_path_matches_flag_off_with_commands(fx, tmp_path):
    from desk_ml.event_path import EventSession

    commands = [cmd("SET_LOTS", "12:00", lots=21), cmd("KILL", "13:50"), cmd("REARM", "14:40")]
    old = replay(fx, tmp_path, commands)
    session = EventSession()
    try:
        new = replay(fx, tmp_path, commands, event_session=session)
        assert compare_boards(old, new) == []
        ledger = {t["trade_id"]: t for t in session.ledger_trades()}
        assert ledger[CUT_ID]["exit_reason"] == "KILL_SWITCH" and ledger[CUT_ID]["status"] == "CLOSED"
    finally:
        session.close()


def test_cut_loss_while_the_risk_engine_raises(fx, tmp_path, monkeypatch):
    from risk_engine import RiskEngine

    from desk_ml.event_path import EventSession

    real = RiskEngine.check_exit

    def broken(self, intent, action="EXIT", now=None):
        if now is not None and now.timestamp() >= at("13:59"):
            raise RuntimeError("risk config corrupt")
        return real(self, intent, action, now)

    monkeypatch.setattr(RiskEngine, "check_exit", broken)
    session = EventSession()
    try:
        board = replay(fx, tmp_path, [cmd("CUT_LOSS", "14:00", trade_id=CUT_ID)], until="14:10", event_session=session)
        row = by_id(board["closed_trades"])[CUT_ID]
        assert row["exit_reason"] == fcb.CUT_LOSS_REASON
        ledger = {t["trade_id"]: t for t in session.ledger_trades()}
        assert ledger[CUT_ID]["status"] == "CLOSED" and ledger[CUT_ID]["exit_reason"] == "FOUNDER_COMMAND"
        alerts = session.audit.rows("HEALTH_ALERT")
        assert any("founder exit mirrored without risk approval" in str(e["payload"].get("reason")) for e in alerts)
        assert board["event_bus"]["handler_errors"] == []
    finally:
        session.close()


# ------------------------------------------------------------- log unit


def test_append_is_idempotent_and_fsynced(tmp_path, monkeypatch):
    import desk_ml.founder_commands.log as fl

    calls = []
    real = fl.os.fsync
    monkeypatch.setattr(fl.os, "fsync", lambda fd: (calls.append(fd), real(fd)))
    row = cmd("STOP", "11:00")
    stored, dup, where = append_command(tmp_path, row)
    assert (dup, where) == (False, "log") and calls
    again, dup2, _ = append_command(tmp_path, {**row, "reason": "resent with other text"})
    assert dup2 and again["reason"] == row["reason"]
    assert len(read_commands(tmp_path).rows) == 1


def test_append_moves_an_unfinished_tail_out_of_the_log(tmp_path):
    path = log_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(cmd("STOP", "11:00")) + "\n" + '{"id": "half', encoding="utf-8")
    append_command(tmp_path, cmd("START", "12:00"))
    res = read_commands(tmp_path)
    assert [r["id"] for r in res.rows] == ["STOP-1100", "START-1200"] and res.problems == []
    assert path.with_name("founder_controls.torn").read_text(encoding="utf-8") == '{"id": "half\n'


def test_exit_commands_spool_when_the_log_cannot_be_written(tmp_path, monkeypatch):
    import desk_ml.founder_commands.log as fl

    monkeypatch.setenv("AAD_FOUNDER_SPOOL_DIR", str(tmp_path / "ram"))
    real = fl._locked

    def full(path):
        if path == log_path(tmp_path):
            raise OSError(28, "No space left on device")
        return real(path)

    monkeypatch.setattr(fl, "_locked", full)
    _, _, where = append_command(tmp_path, cmd("KILL", "13:50"))
    assert where == "spool"
    with pytest.raises(OSError):
        append_command(tmp_path, cmd("START", "14:00"))  # entries are never spooled: not recorded
    assert [r["id"] for r in read_commands(tmp_path).rows] == ["KILL-1350"]
    book = load_book(tmp_path)
    assert book.state_at(at("14:00")).killed_ts == at("13:50")

    monkeypatch.setattr(fl, "_locked", real)  # disk freed: next append drains the spool into the log
    append_command(tmp_path, cmd("REARM", "14:40"))
    assert not fl.spool_path(tmp_path).exists()
    assert [r["id"] for r in read_commands(tmp_path, spool=False).rows] == ["KILL-1350", "REARM-1440"]


def test_validation_shared_by_api_and_engine():
    assert fcb.validate_args("PAUSE", {"minutes": 0}) is None
    assert fcb.validate_args("PAUSE", {"minutes": 99999})
    assert fcb.validate_args("BLOCK_WINDOWS", {"windows": [{"start": "14:45", "end": "14:00"}]})
    assert fcb.validate_args("INDEX", {"underlying": "FINNIFTY", "enabled": True}) is None
    assert fcb.validate_args("INDEX", {"underlying": "nifty", "enabled": True})
    assert fcb.validate_args("ADD_FUNDS", {"amount_inr": -5})
    assert fcb.validate_args("SET_LOTS", {"lots": True})
    assert fcb.validate_row({**cmd("STOP", "11:00"), "reason": " "}) == "reason is required"
