"""Q01 priority (Sahil 2026-10-13): on Q01 days no other NIFTY entry 09:55-10:21 IST; open trades are not force-closed;
Q01 still respects the 10-lot cap (blocked -> Q01_SKIPPED_CAP)."""
from __future__ import annotations

import json

from desk_ml import research_rules as rr

DAY = "2026-10-14"
CFG = {"max_trades_per_day": None, "max_open": 2, "day_stop_losers": 2, "day_stop_net_inr": -25000, "group_stop": {}}
W = rr.Q01_WINDOW


def _r(rid, ent, und="NIFTY", side="PE", strike=22650.0, exit_min=None):
    return {"rule_id": rid, "trade_id": f"{rid}-{ent}", "underlying": und, "side": side, "atm_strike": strike, "entry_min": ent,
            "sig_min": ent, "exit_min": exit_min, "qty": rr.QTY[und]}


def _pass(opens, closed=(), window=W):
    return rr._desk_pass(list(opens), list(closed), DAY, [rr.R01], CFG, q01_window=window)


def test_other_nifty_entry_blocked_inside_window():
    for t in ("09:55", "10:05", "10:21"):
        o, c, blocked, dups, taken = _pass([_r(rr.R01, t)])
        assert not o and blocked[0]["guard"] == rr.BLOCKED_Q01_WINDOW, t
    o, c, blocked, dups, taken = _pass([_r("PX_IB_5", "10:10", side="CE")])
    assert not o and blocked[0]["guard"] == rr.BLOCKED_Q01_WINDOW


def test_allowed_outside_window_and_on_sensex_and_when_not_armed():
    for t in ("09:54", "10:22"):
        o, *_ = _pass([_r(rr.R01, t)])
        assert len(o) == 1, t
    o, *_ = _pass([_r(rr.R01, "10:05", und="SENSEX", strike=72500.0)])
    assert len(o) == 1
    o, *_ = _pass([_r(rr.R01, "10:05")], window=None)
    assert len(o) == 1


def test_q01_entry_allowed_in_window():
    o, c, blocked, dups, taken = _pass([_r(rr.Q01_RULE_ID, "10:01")])
    assert [r["rule_id"] for r in o] == [rr.Q01_RULE_ID] and not blocked


def test_open_trade_from_before_window_not_closed_and_q01_skips_on_cap():
    held = _r(rr.R01, "09:50", side="PE", strike=22600.0)          # still open at 10:01
    q = _r(rr.Q01_RULE_ID, "10:01", side="PE", strike=22650.0)
    o, c, blocked, dups, taken = _pass([held, q])
    assert [r["rule_id"] for r in o] == [rr.R01]                  # kept, not force-closed
    assert blocked[0]["rule_id"] == rr.Q01_RULE_ID and blocked[0]["guard"] == rr.Q01_SKIPPED_CAP


def test_window_from_runner_state(tmp_path):
    p = tmp_path / "data" / "recon" / "paper_extra"
    p.mkdir(parents=True)
    assert rr.q01_priority_window(tmp_path, DAY) == W                       # unknown -> block (fail safe)
    assert rr.q01_priority_window(tmp_path, "2026-10-13") is None           # before Q01 goes live
    for armed, want in ((True, W), (None, W), (False, None)):
        (p / f"{DAY}.json").write_text(json.dumps({"day": DAY, "orders": "REFUSED", "q01": {"armed": armed}, "rows": []}))
        assert rr.q01_priority_window(tmp_path, DAY) == want, armed
