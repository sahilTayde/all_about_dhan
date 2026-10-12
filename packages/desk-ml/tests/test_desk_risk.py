"""Shared desk risk gate (config/desk_risk.yaml). Synthetic rows; no broker; no data/ writes."""

from __future__ import annotations

from desk_ml import desk_risk as dr
from desk_ml import research_rules as rr

DAY = "2026-10-12"


def _row(rid, und, side, ent, ext, net=None, strike=22400.0, tid=None):
    return {"rule_id": rid, "underlying": und, "side": side, "entry_min": ent, "exit_min": ext,
            "spec_exit_min": ext, "sig_min": rr.mplus(ent, -1), "trade_id": tid or f"{rid}-{und}-{side}-{ent}",
            "atm_strike": strike, "realized_pnl_inr": net}


def test_config_file_values() -> None:
    cfg = dr.load_config()
    assert cfg["max_trades_per_day"] is None  # Sahil 2026-10-12: no daily count cap on paper
    assert cfg["max_open"] == 2 and cfg["day_stop_losers"] == 2
    assert cfg["day_stop_net_inr"] == -25000 and cfg["group_stop"]["net_inr"] == -15000


def test_trade_count_cap_is_off_but_code_path_works() -> None:
    taken = [(_row(rr.R01, "NIFTY", "CE", f"12:{10 * i:02d}", f"12:{10 * i + 5:02d}", 100.0), False) for i in range(5)]
    nxt = _row(rr.R01, "NIFTY", "CE", "13:30", "13:50")
    assert dr.check(taken, nxt, dr.load_config()) is None
    assert dr.check(taken, nxt, {**dr.load_config(), "max_trades_per_day": 3}) == dr.RISK_CAP_TRADES


def test_max_open_two() -> None:
    cfg = dr.load_config()
    taken = [(_row(rr.R01, "NIFTY", "CE", "12:00", "12:20"), True), (_row(rr.R01_B3A, "SENSEX", "CE", "12:05", "12:25"), True)]
    assert dr.check(taken, _row(rr.R02, "NIFTY", "CE", "12:10", "12:30"), cfg) == dr.RISK_CAP_OPEN


def test_day_stop_after_two_losers_counts_only_exits_before_entry() -> None:
    cfg = dr.load_config()
    taken = [(_row(rr.R02, "NIFTY", "CE", "10:00", "10:20", -100.0), False),
             (_row(rr.R02, "NIFTY", "CE", "10:30", "10:50", -100.0), False)]
    assert dr.check(taken, _row(rr.R02, "NIFTY", "CE", "10:50", "11:10"), cfg) is None  # 2nd exit same minute
    assert dr.check(taken, _row(rr.R02, "NIFTY", "CE", "10:51", "11:11"), cfg) == dr.RISK_DAY_STOP


def test_day_net_and_group_stop() -> None:
    cfg = dr.load_config()
    big = [(_row(rr.R02, "NIFTY", "CE", "10:00", "10:20", -25000.0), False)]
    assert dr.check(big, _row(rr.R02, "SENSEX", "CE", "10:30", "10:50"), cfg) == dr.RISK_DAY_STOP
    grp = [(_row(rr.R01, "NIFTY", "CE", "10:00", "10:20", -15000.0), False)]
    assert dr.check(grp, _row(rr.R01_B3A, "NIFTY", "CE", "10:30", "10:50"), cfg) == dr.RISK_DAY_STOP
    assert dr.check(grp, _row(rr.R02, "NIFTY", "CE", "10:30", "10:50"), cfg) is None  # other rules not group-stopped
    st = dr.state(grp, cfg)
    assert st["rr_group_net_inr"] == -15000.0 and st["rr_group_stop_hit"] and st["day_stop_hit"] is False


def test_board_risk_state_fields() -> None:
    cfg = dr.load_config()
    taken = [(_row(rr.R01, "NIFTY", "CE", "10:00", "10:20", -100.0), False), (_row(rr.R01, "NIFTY", "CE", "10:30", "10:50"), True)]
    st = dr.state(taken, cfg)
    assert {k: st[k] for k in ("trades_today", "max_trades", "open_now", "max_open", "losers_today",
                               "day_net_inr", "day_stop_hit", "rr_group_net_inr", "halted_reason")} == {
        "trades_today": 2, "max_trades": None, "open_now": 1, "max_open": 2, "losers_today": 1,
        "day_net_inr": -100.0, "day_stop_hit": False, "rr_group_net_inr": -100.0, "halted_reason": None}


def test_desk_pass_order_guard_then_dedup_then_gate() -> None:
    cfg = dr.load_config()
    ce = _row(rr.R01, "NIFTY", "CE", "12:00", "12:20", 10.0)
    pe = _row(rr.R01, "SENSEX", "PE", "12:05", "12:25", 10.0)                     # guard
    dup = _row(rr.R01_B3A, "NIFTY", "CE", "12:00", "12:20", 10.0)                 # dedup
    ce2 = _row(rr.R02, "SENSEX", "CE", "12:06", "12:26", 10.0, strike=72000.0)    # 2nd open: ok
    ce3 = _row(rr.R02, "NIFTY", "CE", "12:07", "12:27", 10.0, strike=22500.0)     # 3rd open: cap
    o, c, blocked, dups, taken = rr._desk_pass([], [ce, pe, dup, ce2, ce3], DAY, [rr.R01, rr.R01_B3A, rr.R02], cfg)
    assert [r["trade_id"] for r in c] == [ce["trade_id"], ce2["trade_id"]]
    assert {b["trade_id"]: b["guard"] for b in blocked} == {pe["trade_id"]: "BLOCKED_OPPOSITE_SIDE",
                                                          ce3["trade_id"]: "RISK_CAP_QTY"}  # NIFTY already 10 lots (qty cap checked before max_open)
    assert [d["trade_id"] for d in dups] == [dup["trade_id"]]


def test_live_entry_block_off_without_env(tmp_path) -> None:
    assert dr.live_entry_block(tmp_path, DAY, environ={}) is None
    j = tmp_path / "data" / "recon" / "research_rules"; j.mkdir(parents=True)
    (j / f"{DAY}.json").write_text('{"risk": {"halted_reason": "RISK_DAY_STOP"}}')
    assert dr.live_entry_block(tmp_path, DAY, environ={"DESK_RISK_GATE_LIVE": "1"}) == "RISK_DAY_STOP"
