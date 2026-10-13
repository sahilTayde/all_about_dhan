"""paper_extra rows go through the desk gate: 2-open limit, -25k day stop, 10-lot cap, on-from minute."""
from __future__ import annotations

import json

from desk_ml import desk_risk
from desk_ml import research_rules as rr

DAY = "2026-10-13"
CFG = {"max_trades_per_day": None, "max_open": 2, "day_stop_losers": 2, "day_stop_net_inr": -25000, "group_stop": {}}


def _px(tmp_path, rows):
    p = tmp_path / "data" / "recon" / "paper_extra"
    p.mkdir(parents=True)
    (p / f"{DAY}.json").write_text(json.dumps({"day": DAY, "orders": "REFUSED", "rows": rows}))
    return rr.paper_extra_rows(tmp_path, DAY)


def _row(rid, und, side, sig, ent, strike=22500.0):
    return {"rule_id": rid, "strategy": rid, "underlying": und, "side": side, "strike": strike, "signal_time": sig,
            "entry_time": ent, "entry_px": 50.0, "status": "OPEN", "mark_time": "12:30", "mark_px": 55.0}


def test_rows_carry_stop_target_fields_and_refuse_orders(tmp_path):
    r = dict(_row("PX_B2", "NIFTY", "CE", "12:00", "12:01"), stop_px=None, target_px=None, exit_rule="x")
    opens, closed = _px(tmp_path, [r])
    assert len(opens) == 1 and not closed
    o = opens[0]
    assert o["qty"] == 650 and o["orders"] == "REFUSED" and o["strategy_name"] == "PX_B2"
    assert {"stop_px", "target_px", "exit_rule"} <= set(o)


def test_third_open_trade_is_blocked(tmp_path):
    rows = [_row("PX_B2", "NIFTY", "CE", "12:00", "12:01"), _row("PX_IB_5", "SENSEX", "CE", "12:01", "12:02", 72500.0),
            _row("PX_ENG_5", "SENSEX", "CE", "12:02", "12:03", 72600.0)]
    opens, closed = _px(tmp_path, rows)
    o, c, blocked, dups, taken = rr._desk_pass(opens, closed, DAY, [], CFG)
    assert [r["rule_id"] for r in o] == ["PX_B2", "PX_IB_5"]
    assert [b["rule_id"] for b in blocked] == ["PX_ENG_5"]


def test_max_open_two_blocks_third_by_gate():
    a = {"rule_id": "A", "entry_min": "12:00", "underlying": "NIFTY"}
    b = {"rule_id": "B", "entry_min": "12:01", "underlying": "SENSEX"}
    assert desk_risk.check([(a, True), (b, True)], {"rule_id": "C", "entry_min": "12:02"}, CFG) == desk_risk.RISK_CAP_OPEN


def test_ten_lot_cap_blocks_second_nifty(tmp_path):
    rows = [_row("PX_B2", "NIFTY", "CE", "12:00", "12:01"), _row("PX_ORB_A", "NIFTY", "CE", "12:01", "12:02", 22550.0)]
    opens, closed = _px(tmp_path, rows)
    o, c, blocked, dups, taken = rr._desk_pass(opens, closed, DAY, [], CFG)
    assert [r["rule_id"] for r in o] == ["PX_B2"]
    assert blocked[0]["guard"] == desk_risk.RISK_CAP_QTY


def test_day_stop_minus_25k_blocks_new_entry(tmp_path):
    rows = [dict(_row("PX_B2", "NIFTY", "CE", "10:00", "10:01"), status="CLOSED", exit_time="10:20", exit_px=10.0, exit_reason="STOP"),
            _row("PX_IB_5", "NIFTY", "CE", "11:00", "11:01")]
    rows[0]["entry_px"] = 50.0
    big = [dict(rows[0])]
    big[0]["entry_px"] = 90.0  # 650 x 80 = -52k loss
    opens, closed = _px(tmp_path, big + [rows[1]])
    o, c, blocked, dups, taken = rr._desk_pass(opens, closed, DAY, [], dict(CFG, day_stop_losers=99))
    assert not o and blocked[0]["guard"] == desk_risk.RISK_DAY_STOP


def test_on_from_moves_earlier_rows_to_history():
    keep, hist = rr.split_on_from([{"rule_id": "PX_B2", "entry_min": "09:16"}, {"rule_id": "PX_B2", "entry_min": "12:10"}],
                                  {"PX_*": "12:06"})
    assert [r["entry_min"] for r in keep] == ["12:10"] and [r["entry_min"] for r in hist] == ["09:16"]
