"""Fault-injection full-day sims of the live loop (spec section 2) and the invariant checker's self-test.

``pytest -m sim`` runs the scenario matrix; the checker self-test runs in the normal suite.
Fixtures are synthetic. Each scenario compares against the no-fault control of the same fixture/path.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from desk_ml.testing.canonical import load_fixture
from desk_ml.testing.sim import DEFAULT_CUTOFFS, IST, Fault, SimResult, check, make_root, run_live_day, ts_at

FAST, FULL = "syn_nifty_live_s23", "syn_multi_3idx_s5"
F = Fault
_CONTROL: dict[tuple[str, str], SimResult] = {}


@pytest.fixture(autouse=True)
def _no_history_files(monkeypatch):
    import desk_ml.paper_scalp as ps

    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})


def _run(fixture: str, flag: str, faults=(), cutoffs=DEFAULT_CUTOFFS) -> SimResult:
    fx = load_fixture(fixture)
    root = make_root(Path(tempfile.mkdtemp(prefix="sim_")), day=fx["day"])
    return run_live_day(root, fx["triples"], day=fx["day"], faults=faults, flag=flag, cutoffs=sorted(set(cutoffs)))


def control(fixture: str, flag: str) -> SimResult:
    if (fixture, flag) not in _CONTROL:
        _CONTROL[(fixture, flag)] = _run(fixture, flag)
    return _CONTROL[(fixture, flag)]


def final(res: SimResult) -> dict[str, dict]:
    return {r["trade_id"]: r for r in res.cycles[-1]["closed"]}


def before(res: SimResult, ts: int) -> dict[str, dict]:
    return {tid: r for tid, r in final(res).items() if int(r["closed_ts"]) < ts}


def hhmm(ts: int) -> str:
    return datetime.fromtimestamp(ts, IST).strftime("%H:%M:%S")


def assert_clean(res: SimResult, **kw) -> None:
    viol = check(res, **kw)
    assert not viol, "\n".join(f"{v.invariant}: {v.detail}" for v in viol[:10])


# ------------------------------------------------------------------ matrix (pytest -m sim)

TAPE_FAULTS = {
    "half_line": ([F("half_line", "11:00", "11:30")], ["11:20"]),
    "corrupt_line": ([F("corrupt_line", "10:00")], []),
    "stall": ([F("stall", "11:00", "11:08")], ["11:05"]),
    "feed_drop": ([F("feed_drop", "12:04", "12:16", args={"underlying": "NIFTY"}), F("chain_drop", "13:00", "13:03")], ["12:10"]),
    "stale_quote": ([F("stale_quote", "11:00", "11:10")], []),
    "none_premium": ([F("none_premium", "12:00", "12:05")], []),
    "dup_out_of_order": ([F("dup_ooo", "13:00", "13:05")], []),
}


@pytest.mark.sim
@pytest.mark.parametrize("flag", ["off", "on"])
@pytest.mark.parametrize("fixture", [FAST, FULL])
def test_control_day_is_clean(fixture, flag):
    res = control(fixture, flag)
    assert all(c["error"] is None for c in res.cycles)
    assert not res.blocks and not res.alerts
    assert_clean(res, control=True)
    assert len(final(res)) >= 4


@pytest.mark.sim
@pytest.mark.parametrize("flag", ["off", "on"])
@pytest.mark.parametrize("scenario", list(TAPE_FAULTS))
def test_tape_faults(scenario, flag):
    faults, extra = TAPE_FAULTS[scenario]
    res = _run(FAST, flag, faults, DEFAULT_CUTOFFS + tuple(extra))
    assert all(c["error"] is None for c in res.cycles), [c["error"] for c in res.cycles]
    assert_clean(res)


@pytest.mark.sim
@pytest.mark.parametrize("flag", ["off", "on"])
def test_founder_stop_then_start_keeps_the_morning_and_blocks_the_window(flag):
    """The proven rewrite: a STOP at 11:00 used to erase every trade booked before it."""
    stop, start = ts_at("2026-09-10", "11:00"), ts_at("2026-09-10", "13:00")
    faults = [F("founder", "11:00", args={"underlying": u, "action": "STOP"}) for u in ("NIFTY", "BANKNIFTY", "SENSEX")]
    faults += [F("founder", "13:00", args={"underlying": u, "action": "START"}) for u in ("NIFTY", "BANKNIFTY", "SENSEX")]
    ctl, res = control(FULL, flag), _run(FULL, flag, faults)
    assert_clean(res)
    assert before(ctl, stop), "control must book trades before 11:00, or this test proves nothing"
    assert before(res, stop) == before(ctl, stop)
    assert any(stop <= int(r["opened_ts"]) < start for r in final(ctl).values()), "control trades in the window"
    assert not any(stop <= int(r["opened_ts"]) < start for r in final(res).values())


@pytest.mark.sim
@pytest.mark.parametrize("flag", ["off", "on"])
def test_human_cancel_applies_once_at_its_time(flag):
    ctl = control(FULL, flag)
    trade = next(r for r in final(ctl).values() if r["filled"] and int(r["closed_ts"]) - int(r["opened_ts"]) >= 600)
    at = int(trade["opened_ts"]) + 120
    res = _run(FULL, flag, [F("override", hhmm(at), args={k: trade[k] for k in ("trade_id", "underlying", "side")})],
               DEFAULT_CUTOFFS + (hhmm(at + 180)[:5],))
    assert_clean(res)
    got = final(res)[trade["trade_id"]]
    assert got["exit_reason"] == "CANCEL_HUMAN" and at <= int(got["closed_ts"]) <= at + 60
    assert before(res, at) == before(ctl, at)


@pytest.mark.sim
@pytest.mark.parametrize("flag", ["off", "on"])
def test_params_change_mid_session_waits_for_next_session(flag):
    res = _run(FAST, flag, [F("params_change", "11:00", args={"params": {"stop_frac": 0.2, "scalp_hold_bars": 3}})])
    assert_clean(res)
    assert final(res) == final(control(FAST, flag))


@pytest.mark.sim
@pytest.mark.parametrize("flag", ["off", "on"])
def test_kill_switch_blocks_from_first_sight_and_releases(flag):
    res = _run(FULL, flag, [F("kill_on", "11:00"), F("kill_off", "13:00")])
    assert_clean(res)
    kill = [b for b in res.blocks if b["kind"] == "KILL_SWITCH"]
    assert len(kill) == 1 and kill[0]["until"] is not None
    first_seen = int(kill[0]["from"])
    assert before(res, first_seen) == before(control(FULL, flag), first_seen)
    assert len([a for a in res.alerts if a["check"] == "entry_block"]) == 1


@pytest.mark.sim
@pytest.mark.parametrize("flag", ["off", "on"])
def test_crash_and_restart_recover_the_same_book(flag):
    res = _run(FULL, flag, [F("crash", "11:10", "12:00"), F("restart", "12:30")], DEFAULT_CUTOFFS + ("12:30",))
    assert [c["hhmm"] for c in res.cycles if c["error"]] == ["11:15", "12:00"]
    assert_clean(res)
    assert final(res) == final(control(FULL, flag))
    assert len([a for a in res.alerts if a["check"] == "paper_engine"]) == 1


@pytest.mark.sim
def test_engine_down_three_cycles_with_open_tickets_flattens_them():
    cut = DEFAULT_CUTOFFS + ("10:20", "10:25", "10:35", "10:40", "10:45")
    res = _run(FULL, "off", [F("crash", "10:25", "10:50")], cut)
    assert_clean(res)
    forced = [r for r in final(res).values() if r["exit_reason"] == "FORCED_ENGINE_FAILURE"]
    assert forced, "the ticket open when the engine died must be closed by the fail-safe"
    assert any(b["kind"] == "ENGINE_FAILED" for b in res.blocks)


@pytest.mark.sim
@pytest.mark.parametrize("flag", ["off", "on"])
def test_restart_every_cycle_changes_nothing(flag):
    res = _run(FAST, flag, [F("restart", h) for h in DEFAULT_CUTOFFS])
    assert_clean(res)
    assert final(res) == final(control(FAST, flag))


@pytest.mark.sim
@pytest.mark.parametrize("seconds", [5, -45, 600, -600])
def test_wall_clock_skew_does_not_change_trades(seconds):
    res = _run(FAST, "off", [F("clock_skew", "09:00", args={"seconds": seconds})])
    assert_clean(res)
    assert final(res) == final(control(FAST, "off"))


CORRUPT = [
    ("halt", "truncated"), ("halt", "directory"), ("halt", "permission"), ("halt", "list"),
    ("founder_view", "list"), ("founder_view", "empty"), ("founder_view", "directory"),
    ("founder_log", "truncated"), ("override_log", "truncated"), ("frozen_params", "truncated"),
    ("booked", "truncated"), ("blocks", "list"), ("risk_yaml", "truncated"), ("risk_yaml", "directory"),
    ("alert_state", "garbage"), ("params", "truncated"),
]


@pytest.mark.sim
@pytest.mark.parametrize("target,how", CORRUPT)
def test_corrupt_control_file_blocks_entries_from_first_sight_and_keeps_history(target, how):
    import os

    if how == "permission" and os.geteuid() == 0:
        pytest.skip("root ignores file permissions")
    res = _run(FULL, "off", [F("corrupt", "11:00", args={"target": target, "how": how})])
    first = ts_at("2026-09-10", "11:15")  # the first cycle after the damage
    harmless = target in ("alert_state", "params", "frozen_params")  # registry reset / frozen snapshot / backup
    assert_clean(res, expect_block_from=None if harmless else first)
    assert before(res, first) == before(control(FULL, "off"), first)
    assert all(c["error"] is None for c in res.cycles)


@pytest.mark.sim
@pytest.mark.parametrize("flag", ["off", "on"])
def test_disk_full_blocks_entries_never_exits_and_recovers(flag):
    res = _run(FULL, flag, [F("disk_full", "11:00", "12:30")])
    assert_clean(res)
    full = [b for b in res.blocks if b["kind"] == "DATA_ROOT_UNWRITABLE"]
    assert len(full) == 1 and full[0]["until"] is not None
    assert all(c["error"] is None for c in res.cycles)


@pytest.mark.sim
@pytest.mark.parametrize("fault,purpose", [("broker_reject", "ENTRY"), ("broker_reject", "EXIT"), ("broker_timeout", None)])
def test_broker_faults_on_the_event_path(fault, purpose):
    res = _run(FULL, "on", [F(fault, "09:30", "12:00", args={"purpose": purpose})])
    assert_clean(res)  # includes: nothing left open at the end, no rewrite, one alert per incident
    start = ts_at("2026-09-10", "09:30")
    assert before(res, start) == before(control(FULL, "on"), start)
    if purpose == "EXIT":
        # The engine books every exit; the broker mirror is retried and alerted once per trade. The
        # desk's ledger still shows that exposure, so new entries fail closed while exits are refused.
        assert any(str(a.get("error_kind", "")).startswith("exit_unmirrored") for a in res.alerts)


# ------------------------------------------------------------------ the checker catches violations


def _fake(cycles, **kw) -> SimResult:
    res = SimResult(day="2026-09-10", flag=kw.pop("flag", "off"), root=Path("."))
    res.cycles = cycles
    for k, v in kw.items():
        setattr(res, k, v)
    return res


def _row(tid, opened, closed, **kw):
    return {"trade_id": tid, "underlying": "NIFTY", "side": "CE", "opened_ts": opened, "closed_ts": closed, "lots": 20,
            "filled": True, "exit_reason": "TARGET", "realized_pnl_inr": 10.0, "gross_pnl_inr": 10.0, **kw}


def _cycle(hh, closed=(), opened=(), **kw):
    ts = ts_at("2026-09-10", hh)
    return {"k": 0, "cutoff": ts, "hhmm": hh, "error": None, "tape_cut": {"NIFTY": ts}, "closed": list(closed),
            "open": list(opened), "overall_pnl_inr": sum(r["realized_pnl_inr"] for r in closed), "event_bus": {}, **kw}


T = lambda hh: ts_at("2026-09-10", hh)  # noqa: E731


@pytest.mark.parametrize("inv,res", [
    ("I1", _fake([_cycle("11:00", [_row("a", T("10:00"), T("10:30"), lots=30)])])),
    ("I2", _fake([_cycle("15:30", [], [{"trade_id": "o", "underlying": "NIFTY", "side": "CE", "opened_ts": T("15:00")}])])),
    ("I3", _fake([_cycle("12:00", [_row("a", T("11:30"), T("11:40"))])],
                 blocks=[{"kind": "KILL_SWITCH", "from": T("11:00"), "until": None}])),
    ("I4", _fake([{**_cycle("11:00", [_row("a", T("10:00"), T("10:30"))]), "overall_pnl_inr": 999.0}])),
    ("I5", _fake([_cycle("11:00", [_row("a", T("10:00"), T("10:30"), exit_reason="")])])),
    ("I6", _fake([_cycle("11:00", [_row("a", T("10:00"), T("10:30"))]), _cycle("12:00", [])])),
    ("I6", _fake([_cycle("11:00", []), _cycle("12:00", [_row("b", T("10:40"), T("11:30"))])])),
    ("I7", _fake([_cycle("11:00")], alerts=[{"session": "d", "check": "c", "error_kind": "k"}] * 2)),
    ("I9", _fake([_cycle("11:00")], model_log=[{"session": "d", "event": "OPEN", "tick_ts": 1}] * 2)),
    ("I10", None),
])
def test_checker_catches_each_violation(inv, res):
    if inv == "I10":
        res = _fake([_cycle("12:00", [_row("a", T("11:30"), T("11:40"))])])
        assert any(v.invariant == "I10" for v in check(res, expect_block_from=T("11:15")))
        return
    assert any(v.invariant == inv for v in check(res)), check(res)


def test_checker_passes_a_clean_day():
    res = _fake([_cycle("11:00", [_row("a", T("10:00"), T("10:30"))]),
                 _cycle("12:00", [_row("a", T("10:00"), T("10:30")), _row("b", T("11:10"), T("11:40"))])])
    assert check(res, control=True) == []
