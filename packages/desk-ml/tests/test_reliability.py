"""PR-A reliability units: atomic writes, alert sink, founder/override logs, entry guard, blocks,
booked-trade guard, model log, tape validation. Each ``test_spof_<ID>`` pins a spec section-5 row."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

import desk_ml.founder_session as fs
import desk_ml.paper_scalp as ps
from desk_ml.features import Triple
from desk_ml.reliability import AlertSink, ModelLogSink, ReplayContext, atomic_write_json, read_jsonl

IST = timezone(timedelta(hours=5, minutes=30))
DAY = "2026-09-10"


def at(hh: int, mm: int = 0, ss: int = 0) -> int:
    return int(datetime(2026, 9, 10, hh, mm, ss, tzinfo=IST).timestamp())


def _tick(ts: int) -> Triple:
    return Triple(
        ts=ts, idx_close=23200.0, ce_close=120.0, pe_close=80.0, atm_strike=23200.0,
        itm_ce_close=160.0, itm_ce_strike=23000.0,
        wing_quotes={"23000": {"ce": 160.0, "pe": 20.0}, "23200": {"ce": 120.0, "pe": 80.0}},
    )


def try_open(root, ts: int, *, ctx=None, book="MIX-ML-LOGIT") -> ps.BookEngine:
    """One CE entry attempt on a TREND-UP tick that opens when every gate passes."""
    engine = ps.BookEngine(root=root, ctx=ctx, nifty_allow_sides=("CE", "PE"), nifty_need_strength=True,
                           nifty_align_impulse=True)
    engine.lot_by_und["NIFTY"] = (65, "test")
    engine.starting_capital = 570000.0
    engine.last_regime["NIFTY"] = {
        "regime": "TREND", "direction": "UP", "last3_impulse": "UP", "last3_reason": "pause_continue",
        "itm_bin": {"side": "CE", "ce_votes": ["CE_SHORT_COVER"], "pe_votes": []},
    }
    ps._try_open(engine, book_id=book, underlying="NIFTY", side="CE", tick=_tick(ts), ce_path=[120.0],
                 pe_path=[80.0], bar_i=10)
    return engine


def reasons(engine) -> list[str]:
    return [s.get("reason") for s in engine.skips]


# ------------------------------------------------------------------ atomic writes / jsonl


def test_spof_S15_atomic_write_keeps_the_old_file_when_replace_fails(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    atomic_write_json(path, {"v": 1})

    def boom(*_a, **_k):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        atomic_write_json(path, {"v": 2})
    assert json.loads(path.read_text()) == {"v": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["state.json"]  # no temp file left behind


def test_read_jsonl_ignores_an_append_in_progress_but_not_mid_file_damage(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_text('{"a": 1}\n{"a": 2')
    assert read_jsonl(path) == [{"a": 1}]
    path.write_text('{"a": 1}\n{"a": \n{"a": 3}\n')
    with pytest.raises(ValueError):
        read_jsonl(path)
    path.write_text("[1, 2]\n")
    with pytest.raises(ValueError):
        read_jsonl(path)
    assert read_jsonl(tmp_path / "missing.jsonl") is None


# ------------------------------------------------------------------ alert sink


def test_alert_sink_dedupes_across_restarts_and_never_raises(tmp_path, monkeypatch):
    import desk_ml.reliability as rel

    assert AlertSink(tmp_path).emit(session=DAY, check="c", kind="k", message="m") is True
    rel._UNSAVED_STATE.clear()  # a restart
    assert AlertSink(tmp_path).emit(session=DAY, check="c", kind="k", message="m") is False
    lines = (tmp_path / "data" / "health" / "alerts.jsonl").read_text().splitlines()
    assert len(lines) == 1

    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "data").write_text("a file where the data folder should be")
    assert AlertSink(bad).emit(session=DAY, check="c", kind="k", message="m") is True  # stderr, no raise


def test_alert_sink_quarantines_corrupt_state_and_queues_alerts_while_disk_is_full(tmp_path, monkeypatch):
    import desk_ml.reliability as rel

    state = tmp_path / "data" / "health" / "alert_state.json"
    state.parent.mkdir(parents=True)
    state.write_text("{not json")
    sink = AlertSink(tmp_path)
    assert sink.first_seen(DAY, "c", "k") is None
    assert any(p.name.startswith("alert_state.json.corrupt.") for p in state.parent.iterdir())

    real = rel.append_line
    monkeypatch.setattr(rel, "append_line", lambda *_a, **_k: (_ for _ in ()).throw(OSError(28, "full")))
    assert sink.emit(session=DAY, check="c", kind="queued", message="m") is True
    monkeypatch.setattr(rel, "append_line", real)
    assert sink.flush_pending() is True
    rows = [json.loads(x) for x in (tmp_path / "data" / "health" / "alerts.jsonl").read_text().splitlines()]
    assert [r["error_kind"] for r in rows] == ["queued"]


# ------------------------------------------------------------------ founder log


def test_founder_default_is_stop_when_file_missing(tmp_path):
    assert fs.fill_decision_at("NIFTY", root=tmp_path, ts=at(10))["allow"] is False
    with pytest.raises(fs.FounderStateError):
        fs.fill_decision_at("NIFTY", root=None, ts=at(10))  # no root: never this checkout's file


def test_founder_stop_applies_from_its_timestamp_only(tmp_path):
    fs.save_founder_book(["NIFTY"], root=tmp_path, ts=0.0)
    fs.set_index_trade("NIFTY", "STOP", root=tmp_path, ts=float(at(12, 30)))
    assert fs.fill_decision_at("NIFTY", root=tmp_path, ts=at(11, 30))["allow"] is True
    assert fs.fill_decision_at("NIFTY", root=tmp_path, ts=at(12, 30))["allow"] is False
    fs.set_index_trade("NIFTY", "START", root=tmp_path, ts=float(at(13)))
    assert fs.fill_decision_at("NIFTY", root=tmp_path, ts=at(12, 45))["allow"] is False  # START is not retroactive
    assert fs.fill_decision_at("NIFTY", root=tmp_path, ts=at(13, 1))["allow"] is True
    assert fs.load_founder_book(tmp_path)["trade_underlyings"] == ["NIFTY"]  # the UI view follows


def test_first_write_seeds_the_json_state_as_baseline(tmp_path):
    recon = tmp_path / "data" / "recon"
    recon.mkdir(parents=True)
    (recon / "founder_trade_underlyings.json").write_text('{"trade_underlyings": ["NIFTY"]}')
    fs.set_index_trade("SENSEX", "START", root=tmp_path, ts=float(at(12)))
    rows = fs.read_commands(tmp_path)
    assert rows[0] == {**rows[0], "ts": 0.0, "underlying": "NIFTY", "source": fs.BASELINE_SOURCE}
    assert fs.fill_decision_at("NIFTY", root=tmp_path, ts=at(9, 30))["allow"] is True
    assert fs.fill_decision_at("SENSEX", root=tmp_path, ts=at(11))["allow"] is False
    assert fs.fill_decision_at("SENSEX", root=tmp_path, ts=at(12))["allow"] is True
    # A session before the log existed keeps the legacy meaning: the file's current state.
    assert fs.fill_decision_at("SENSEX", root=tmp_path, ts=at(10) - 86400)["allow"] is True


def test_owner_harness_monkeypatch_still_works(tmp_path, monkeypatch):
    monkeypatch.setattr(fs, "allows_new_fill", lambda underlying, root=None: True)
    assert fs.fill_decision_at("SENSEX", root=tmp_path, ts=at(10))["allow"] is True


@pytest.mark.parametrize("content", ["[1, 2]", '{"trade_underlyings": "NIFTY"}', "{not json", ""])
def test_spof_S3_unreadable_founder_state_fails_closed_for_nifty(tmp_path, content):
    recon = tmp_path / "data" / "recon"
    recon.mkdir(parents=True)
    (recon / "founder_trade_underlyings.json").write_text(content)
    engine = try_open(tmp_path, at(10, 30))
    assert not engine.opens
    assert reasons(engine) == [fs.UNREADABLE_REASON]


def test_spof_S3_nifty_opens_when_started(founder_root):
    assert try_open(founder_root, at(10, 30)).opens  # the positive control for the test above


def test_spof_S3_corrupt_founder_log_fails_closed(tmp_path):
    fs.save_founder_book(["NIFTY"], root=tmp_path, ts=0.0)
    with open(fs.log_path(tmp_path), "a") as fh:
        fh.write('{"ts": 5, "underlying": "NIFTY"\n{"ok": 1}\n')
    engine = try_open(tmp_path, at(10, 30))
    assert not engine.opens and reasons(engine) == [fs.UNREADABLE_REASON]


def test_live_view_hand_edit_is_ingested_with_the_time_it_was_seen(tmp_path):
    fs.save_founder_book(["NIFTY"], root=tmp_path, ts=0.0)
    view = fs.session_path(tmp_path)
    blob = json.loads(view.read_text())
    blob["trade_underlyings"] = []
    view.write_text(json.dumps(blob))  # someone edits the JSON by hand at 12:30
    fs.ingest_view_edits(tmp_path, ts=float(at(12, 30)))
    assert fs.fill_decision_at("NIFTY", root=tmp_path, ts=at(12))["allow"] is True
    assert fs.fill_decision_at("NIFTY", root=tmp_path, ts=at(12, 31))["allow"] is False


# ------------------------------------------------------------------ human overrides


def _open_pos(trade_id="t1") -> ps.OpenPaper:
    return ps.OpenPaper(book_id="MIX-DEFAULT-BUY", underlying="NIFTY", side="CE", trade_id=trade_id, entry=150.0,
                        stop=140.0, target=170.0, atm_strike=23000.0, opened_ts=at(10), opened_bar=0,
                        strike_source="ITM_100", limit_price=150.0, lot_size=65, lots=20, qty=1300, filled=True,
                        last_ltp=150.0, index_regime="TREND")


def _mtm(engine, ts):
    tick = Triple(ts=ts, idx_close=23200.0, ce_close=150.0, pe_close=80.0, atm_strike=23200.0,
                  itm_ce_close=151.0, itm_ce_strike=23000.0, wing_quotes={"23000": {"ce": 151.0, "pe": 20.0}})
    ps.mark_to_market(engine, tick, "NIFTY", 5)


def test_override_applies_from_its_timestamp_and_the_engine_never_writes_it(tmp_path):
    ps.save_human_override({"action": "CANCEL", "trade_id": "t1", "underlying": "NIFTY", "side": "CE"},
                           root=tmp_path, ts=float(at(11)))
    files = {p: p.read_bytes() for p in (tmp_path / "data" / "recon").iterdir()}
    for _ in range(2):  # re-replaying the day gives the same result every time
        engine = ps.BookEngine(root=tmp_path)
        engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = _open_pos()
        _mtm(engine, at(10, 30))
        assert engine.opens, "an 11:00 cancel must not act at 10:30"
        _mtm(engine, at(11, 0, 20))
        assert not engine.opens and engine.closed[-1]["exit_reason"] == ps.CANCEL_HUMAN
        assert engine.closed[-1]["closed_ts"] == at(11, 0, 20)
    assert {p: p.read_bytes() for p in (tmp_path / "data" / "recon").iterdir()} == files


def test_override_clear_drops_a_pending_instruction(tmp_path):
    ps.save_human_override({"action": "CANCEL", "trade_id": "t1"}, root=tmp_path, ts=float(at(10, 20)))
    ps.save_human_override({"action": "CLEAR"}, root=tmp_path, ts=float(at(10, 25)))
    engine = ps.BookEngine(root=tmp_path)
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = _open_pos()
    _mtm(engine, at(10, 30))
    assert engine.opens, engine.closed  # the cancel was cleared before any tick could apply it


# ------------------------------------------------------------------ entry guard / blocks


def test_spof_S5_live_blocks_stop_entries_only_inside_their_interval(founder_root):
    ctx = ReplayContext(root=founder_root, live_loop=True, entry_blocks=(("KILL_SWITCH", float(at(11)), float(at(12))),))
    assert try_open(founder_root, at(10, 59), ctx=ctx).opens
    blocked = try_open(founder_root, at(11, 30), ctx=ctx)
    assert not blocked.opens and reasons(blocked) == ["KILL_SWITCH"]
    assert try_open(founder_root, at(12), ctx=ctx).opens


def test_spof_S5_live_risk_limits_run_on_the_flag_off_path(founder_root, tmp_path):
    import yaml

    from desk_ml.persist import code_root

    cfg = yaml.safe_load((code_root() / "config" / "risk_limits.yaml").read_text())
    cfg["modes"]["paper"]["max_lots_per_trade"] = 5
    risk = tmp_path / "risk.yaml"
    risk.write_text(yaml.safe_dump(cfg))
    engine = try_open(founder_root, at(10, 30), ctx=ReplayContext(root=founder_root, live_loop=True, risk_config=risk))
    assert not engine.opens
    veto = engine.skips[-1]
    assert veto["reason"] == "RISK_VETO" and veto["reason_code"] == "MAX_LOTS"
    risk.write_text("{broken")
    engine = try_open(founder_root, at(10, 30), ctx=ReplayContext(root=founder_root, live_loop=True, risk_config=risk))
    assert not engine.opens and engine.skips[-1]["reason_code"] == "ENGINE_ERROR"  # entries fail closed


def test_guard_state_is_as_of_the_tick_across_indices():
    from desk_ml.paper_guard import state_at

    engine = ps.BookEngine()
    engine.closed = [
        {"filled": True, "opened_ts": at(10), "closed_ts": at(11), "realized_pnl_inr": -500.0},
        {"filled": True, "opened_ts": at(14), "closed_ts": at(14, 49), "realized_pnl_inr": -90000.0},
    ]
    early = state_at(engine, at(10, 30))
    assert early["open_positions"] == 1 and early["realized_pnl_today"] == 0.0
    assert state_at(engine, at(12))["realized_pnl_today"] == -500.0  # not the 14:49 loss


def test_block_registry_intervals_sticky_and_corrupt(tmp_path):
    from desk_ml.live_cycle import BlockRegistry

    reg = BlockRegistry(tmp_path, DAY, alerts=AlertSink(tmp_path))
    reg.update({"KILL_SWITCH": (None, "file"), "PARAMS_UNREADABLE": (None, "x")}, at(11))
    reg.add_sticky("HISTORY_REWRITE", at(11, 30), "diff")
    assert ("KILL_SWITCH", at(11), None) in reg.intervals()  # add_sticky did not close it
    reg.update({}, at(12))
    got = {k: (lo, hi) for k, lo, hi in BlockRegistry(tmp_path, DAY, alerts=AlertSink(tmp_path)).intervals()}
    assert got["KILL_SWITCH"] == (at(11), at(12))
    assert got["PARAMS_UNREADABLE"] == (at(11), None) and got["HISTORY_REWRITE"] == (at(11, 30), None)
    reg.path.write_text("[1, 2]")
    fresh = BlockRegistry(tmp_path, DAY, alerts=AlertSink(tmp_path), clock=lambda: datetime.fromtimestamp(at(13), IST))
    assert fresh.intervals() == [("BLOCK_REGISTRY_UNREADABLE", at(13), None)]


# ------------------------------------------------------------------ booked-trade guard


def _row(tid, opened, closed, net=100.0, filled=True):
    return {"trade_id": tid, "book_id": "MIX-DEFAULT-BUY", "underlying": "NIFTY", "side": "CE", "atm_strike": 23000.0,
            "opened_ts": opened, "closed_ts": closed, "entry": 150.0, "exit": 151.0, "qty": 1300, "lots": 20,
            "exit_reason": "TARGET", "gross_pnl_inr": net, "charges_inr": 0.0, "realized_pnl_inr": net, "filled": filled}


def test_booked_trades_cannot_vanish_change_or_appear_in_the_past(tmp_path):
    from desk_ml.live_cycle import HISTORY_RECONCILED, guard_history, read_booked

    ctx = ReplayContext(root=tmp_path, session_ist_date=DAY, live_loop=True)
    tape = {"NIFTY": [_tick(at(11))]}
    engine = ps.BookEngine(root=tmp_path)
    engine.closed = [_row("a", at(10), at(10, 30))]
    assert guard_history(engine, tape, ctx)["status"] == "OK"
    engine = ps.BookEngine(root=tmp_path)
    engine.closed = [_row("b", at(10, 40), at(10, 50))]  # "a" vanished; "b" appeared before 11:00
    rep = guard_history(engine, {"NIFTY": [_tick(at(12))]}, ctx)
    assert rep["status"] == HISTORY_RECONCILED and len(rep["reconciled"]) == 2 and not rep["unreconcilable"]
    assert [r["trade_id"] for r in engine.closed] == ["a"]  # the board shows the booked truth
    assert set(read_booked(tmp_path, DAY)) == {"a"}


def _rolled_tick(ts: int, *, booked_px=None) -> Triple:
    """The tape's ITM PE leg rolled to 23550 (121.9); the booked 23650 PE is only in the wing cells."""
    wings = {"23550": {"ce": 30.0, "pe": 121.9}}
    if booked_px is not None:
        wings["23650"] = {"ce": 25.0, "pe": booked_px}
    return Triple(ts=ts, idx_close=23500.0, ce_close=90.0, pe_close=95.0, atm_strike=23500.0,
                  itm_pe_close=121.9, itm_pe_strike=23550.0, wing_quotes=wings)


def _pe_23650(trade_id="pe1", last_ltp=205.0) -> ps.OpenPaper:
    return ps.OpenPaper(book_id="MIX-DEFAULT-BUY", underlying="NIFTY", side="PE", trade_id=trade_id, entry=209.75,
                        stop=190.0, target=240.0, atm_strike=23650.0, opened_ts=at(14, 9, 43), opened_bar=0,
                        strike_source="ITM_100", limit_price=209.75, lot_size=65, lots=20, qty=1300, filled=True,
                        last_ltp=last_ltp, index_regime="TREND")


def test_F2_forced_exit_prices_the_booked_strike_after_the_itm_strike_rolled():
    from desk_ml.live_cycle import booked_quote

    px, meta = booked_quote(_pe_23650(), [_rolled_tick(at(14, 19), booked_px=204.5), _rolled_tick(at(14, 20), booked_px=204.5)])
    assert px == 204.5 and meta["quote_src"] == "STRIKE_23650" and meta["quote_stale"] is False


def test_F2_booked_strike_missing_now_uses_its_last_known_quote_flagged_stale():
    from desk_ml.live_cycle import booked_quote

    ticks = [_rolled_tick(at(14, 15), booked_px=201.0), _rolled_tick(at(14, 20))]  # no 23650 quote at 14:20
    px, meta = booked_quote(_pe_23650(), ticks)
    assert px == 201.0 and meta["quote_stale"] is True and meta["quote_ts"] == at(14, 15)
    px, meta = booked_quote(_pe_23650(last_ltp=203.0), [_rolled_tick(at(14, 20))])
    assert px == 203.0 and meta["quote_src"] == "LAST_MARK_BOOKED_STRIKE" and meta["quote_stale"] is True
    assert px != 121.9  # never the rolled 23550 PE


def test_an_open_ticket_that_cannot_be_carried_is_closed_at_its_booked_strike(tmp_path):
    from desk_ml.live_cycle import FORCED_HISTORY_CLOSE, HISTORY_UNRECONCILABLE, guard_history

    ctx = ReplayContext(root=tmp_path, session_ist_date=DAY, live_loop=True)
    engine = ps.BookEngine(root=tmp_path)
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = _pe_23650()
    guard_history(engine, {"NIFTY": [_rolled_tick(at(14, 10), booked_px=207.0)]}, ctx)
    engine = ps.BookEngine(root=tmp_path)  # next cycle: gone, and no Pins to carry it
    rep = guard_history(engine, {"NIFTY": [_rolled_tick(at(14, 20), booked_px=204.5)]}, ctx)
    assert rep["status"] == HISTORY_UNRECONCILABLE
    row = engine.closed[-1]
    assert row["trade_id"] == "pe1" and row["exit_reason"] == FORCED_HISTORY_CLOSE
    assert row["exit"] == 204.5 and row["quote_src"] == "STRIKE_23650"  # not 121.9 (the 23550 PE)


def test_F2_failsafe_flatten_prices_the_booked_strike_from_the_raw_tape(tmp_path, monkeypatch):
    from dataclasses import asdict

    from desk_ml.live_cycle import FORCED_ENGINE_CLOSE, booked_state_path, failsafe_flatten, read_booked
    from desk_ml.tape import dual_tape_dir

    monkeypatch.setattr("desk_ml.tape.load_dual_tape_triples", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("loader down")))
    booked_state_path(tmp_path, DAY).parent.mkdir(parents=True)
    booked_state_path(tmp_path, DAY).write_text(json.dumps({"cutoff_ts": {}, "open": {"pe1": asdict(_pe_23650())}}))
    snap = {"underlying": "NIFTY", "index_ltp": 23300.0, "atm_strike": 23300.0, "atm_pe_ltp": 60.0,
            "itm_pe_ltp": 108.0, "itm_pe_strike": 23200.0, "atm_ce_ltp": 70.0, "itm_ce_ltp": 150.0,
            "itm_ce_strike": 23100.0, "wing_quotes": {"23650": {"ce": 20.0, "pe": 168.15}}}
    folder = dual_tape_dir(tmp_path)
    folder.mkdir(parents=True)
    (folder / f"{DAY}.jsonl").write_text(json.dumps({"as_of_ist": "2026-09-10T14:30:00+05:30", "underlyings": [snap]}) + "\n")
    assert failsafe_flatten(tmp_path, DAY) == ["pe1"]
    row = read_booked(tmp_path, DAY)["pe1"]
    assert row["exit_reason"] == FORCED_ENGINE_CLOSE and row["exit"] == 168.15  # not 108.0 (the 23200 PE)


# ------------------------------------------------------------------ model log


def test_model_log_rereplay_writes_each_event_once_and_aggregates_holds(tmp_path):
    def cycle(last_min: int):
        sink = ModelLogSink(tmp_path, DAY)
        for m in range(0, last_min + 1):
            sink.set_tick("NIFTY", at(10, m))
            sink.write({"event": "HOLD", "book_id": "B", "reason": "GATE"})
            sink.write({"event": "HOLD", "book_id": "B", "reason": "GATE"})
            if m == 2:
                sink.write({"event": "OPEN", "trade_id": "t", "book_id": "B"})
        sink.flush()

    for last in (3, 3, 5, 5, 8):
        cycle(last)
    rows = [json.loads(x) for x in (tmp_path / "data" / "recon" / "model_log" / f"{DAY}.jsonl").read_text().splitlines()]
    assert sum(1 for r in rows if r["event"] == "OPEN") == 1
    holds = [r for r in rows if r["event"] == "HOLD"]
    assert [r["count"] for r in holds] == [2] * len(holds)
    assert sorted(r["tick_ts"] for r in holds) == [at(10, m) for m in range(8)]  # one row per closed minute


def test_model_log_cap_stops_writes_with_one_alert(tmp_path):
    sink = ModelLogSink(tmp_path, DAY, alerts=AlertSink(tmp_path), cap_bytes=10)
    sink.set_tick("NIFTY", at(10))
    sink.write({"event": "OPEN", "trade_id": "t"})
    sink.flush()
    assert not sink.path.exists()
    assert "cap_reached" in (tmp_path / "data" / "health" / "alerts.jsonl").read_text()


# ------------------------------------------------------------------ tape


def test_spof_S14_mid_file_damage_is_counted_and_the_live_loop_drops_non_finite_prices(tmp_path):
    from desk_ml.tape import dual_tape_dir, load_dual_tape_triples
    from desk_ml.testing.canonical import tape_lines
    from desk_ml.event_parity import synthetic_triples

    lines = [ln for _ts, ln in tape_lines({"NIFTY": synthetic_triples(day=DAY, step_s=60)[:30]})]
    blob = json.loads(lines[10])
    blob["underlyings"][0]["itm_ce_ltp"] = float("nan")
    lines[10] = json.dumps(blob)
    lines.insert(5, '{"as_of_ist": "2026-09-10T10:00:00+05:30", "underly')
    folder = dual_tape_dir(tmp_path)
    folder.mkdir(parents=True)
    (folder / f"{DAY}.jsonl").write_text("\n".join(lines) + "\n" + lines[-1][:20])  # tail still being written
    legacy, meta = load_dual_tape_triples("NIFTY", root=tmp_path, session_ist_date=DAY)
    strict, meta_s = load_dual_tape_triples("NIFTY", root=tmp_path, session_ist_date=DAY, strict=True)
    assert meta["skipped_lines"] == 1 and meta_s["skipped_lines"] == 1
    assert len(legacy) == 30 and len(strict) == 29
    assert all(t.itm_ce_close == t.itm_ce_close for t in strict)  # no NaN reaches the live engine


def test_spof_S1_dashboard_beats_never_claim_alive(tmp_path):
    board = {"heartbeat": {"as_of_ist": "2026-09-10T09:00:00+05:30"}}
    ps.refresh_dashboard_clock(board, tick_seconds=2, root=tmp_path)  # no successful cycle on record
    assert board["heartbeat"]["alive"] is False
    assert board["heartbeat"]["as_of_ist"] == "2026-09-10T09:00:00+05:30"


def test_F3_root_cause_live_logit_sees_the_same_bars_in_every_cycle():
    """The newest tick used to see a partial 3m bar that later cycles never show that tick."""
    from desk_ml.event_parity import synthetic_triples
    from desk_ml.testing.canonical import load_fixture

    hist = {}
    for k, day in enumerate(("2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-07", "2026-09-08", "2026-09-09")):
        hist.update({int(t.ts): t.idx_close for t in synthetic_triples(day=day, seed=300 + k, step_s=60)})
    tr = load_fixture("syn_multi_3idx_s5")["triples"]["NIFTY"][:320]
    full_live, _ = ps.logit_side_series(tr, index_closes=hist, causal_bars=True)
    full_legacy, _ = ps.logit_side_series(tr, index_closes=hist)
    assert sum(1 for r in full_live if r.get("side")) > 100, "the logit must be active for this test to mean anything"
    legacy_drift = live_drift = 0
    for i in range(60, len(tr), 4):
        live, _ = ps.logit_side_series(tr[: i + 1], index_closes=hist, causal_bars=True)
        legacy, _ = ps.logit_side_series(tr[: i + 1], index_closes=hist)
        live_drift += live[-1].get("side") != full_live[i].get("side")
        legacy_drift += legacy[-1].get("side") != full_legacy[i].get("side")
    assert live_drift == 0
    assert legacy_drift > 0  # the mechanism that made a booked ticket vanish on the next cycle


def test_crashed_append_is_repaired_before_the_next_record(tmp_path):
    from desk_ml.reliability import append_line

    path = tmp_path / "log.jsonl"
    append_line(path, '{"a": 1}')
    with open(path, "a") as fh:
        fh.write('{"a": 2, "b"')  # the process died mid-append
    append_line(path, '{"a": 3}')
    assert read_jsonl(path) == [{"a": 1}, {"a": 3}]
    assert (tmp_path / "log.jsonl.quarantine").read_text() == '{"a": 2, "b"\n'
    with open(path, "a") as fh:
        fh.write('{"a": 4}')  # complete record, newline lost: kept, not quarantined
    append_line(path, '{"a": 5}')
    assert [r["a"] for r in read_jsonl(path)] == [1, 3, 4, 5]


def test_a_glued_line_yields_its_complete_record_and_real_damage_still_fails_closed(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_text('{"a": 1}\n{"a": 2, "b{"a": 3}\n')  # written before repair_tail existed
    assert read_jsonl(path) == [{"a": 1}, {"a": 3}]
    path.write_text('{"a": 1}\nnot json at all\n')
    with pytest.raises(ValueError):
        read_jsonl(path)


def test_wipe_updates_both_frozen_params_copies(tmp_path):
    from desk_ml.live_cycle import frozen_params_path, read_frozen_params, write_frozen_params

    day = ps.datetime.now(IST).date().isoformat()
    write_frozen_params(tmp_path, day, {"session": day, "params": {"stop_frac": 0.38}})
    out = ps.wipe_today_paper_book(root=tmp_path, ist_date=day)
    frozen_params_path(tmp_path, day).write_text("{broken")  # the primary is damaged after the wipe
    snap = read_frozen_params(tmp_path, day)
    assert snap["params"]["paper_book_epoch_ts"] == out["paper_book_epoch_ts"] and snap["wiped_ts"]
