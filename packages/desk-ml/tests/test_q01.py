"""Q01 ITM100 v1.1 + Q01_T15 shadow: port of research 2026-10-13_q01_exits/run_a.py sim(), checked on its 73 real-price days."""
import json
from pathlib import Path

from desk_ml import q01

FIXDIR = Path(__file__).parent / "fixtures" / "q01"
FX = json.load(open(FIXDIR / "q01_fixture.json"))


def run(x, v, now_m=None):
    idx = {int(k): v_ for k, v_ in x["idx"].items()}
    opt = {int(k): tuple(v_) for k, v_ in x["opt"].items()}
    return q01.simulate(sg=x["sg"], s10=x["S0"], idx=idx, opt=opt, variant=v, now_m=now_m)


def _m(s):
    return int(s[:2]) * 60 + int(s[3:5])


def test_side_and_strike_all_days():
    for x in FX:
        assert q01.side_strike(x["open_hist"], x["S0"]) == (x["sg"], x["side"], x["K"]), x["day"]


def test_plain_and_t15_match_research_real_price_trades():
    n = 0
    for x in FX:
        for v in ("PLAIN", "T15"):
            e = x["expected"][v]
            r = run(x, v)
            if not e["ok"]:
                assert r["status"] != "CLOSED", (x["day"], v)
                continue
            assert r["status"] == "CLOSED", (x["day"], v, r)
            assert (r["exit_min"], r["exit_reason"], r["entry_px"], r["exit_px"]) == (q01.hm(e["xm"]), e["kind"], e["en"], e["ex"]), (x["day"], v)
            n += 1
    assert n >= 140


def test_live_never_uses_future_minutes():
    for x in FX[:20]:
        full = run(x, "PLAIN")
        for now in range(600, 625):
            r = run(x, "PLAIN", now_m=now)
            if r["status"] == "CLOSED":
                assert r == full and _m(r["exit_min"]) <= now
            elif r["status"] == "OPEN":
                assert _m(r["mark_min"]) <= now and _m(r["entry_min"]) <= now


def test_vix_filter_reproduces_armed_days():
    V = json.load(open(FIXDIR / "vix_daily_hist.json"))
    for x in FX:
        assert q01.vix_filter(V, x["day"])["armed"], x["day"]


def test_vix_filter_arms_no_other_day():
    V = json.load(open(FIXDIR / "vix_daily_hist.json"))
    A = json.load(open(FIXDIR / "armed_days.json"))
    armed = {d for d in A["days"] if q01.vix_filter(V, d)["armed"]}
    # 2026-05-13 is armed but mv = 0 (official open 23,362.45 == 10:00 close): no trade by rule (2026-10-12_q01_match/REPORT.md)
    assert armed - set(A["armed_expected"]) == {"2026-05-13"}
    assert set(A["armed_expected"]) <= armed


def test_no_trade_when_mv_zero():
    assert q01.side_strike(22500.0, 22500.0) is None


def test_t15_target_px_and_index_stop_are_sent():
    x = FX[0]
    r = run(x, "T15")
    assert r["target_px"] == round(r["entry_px"] + 1.5 * (0.3 * r["entry_px"]), 2)
    assert r["index_stop"] == round(x["S0"] - x["sg"] * 0.3 * r["entry_px"] / 0.54, 2)
    assert r["planned_exit"] == "10:21"


def test_official_open_never_uses_0915_tick(tmp_path):
    import base64
    import struct

    def frame(ts, v):
        pkt = struct.pack("<BHBi", 2, 16, 0, 13) + struct.pack("<f", v) + b"\0" * 4
        return json.dumps({"recv_ts": f"2026-10-14T{ts}+05:30", "raw_b64": base64.b64encode(pkt).decode()})

    (tmp_path / "raw_frames.jsonl").write_text("\n".join([frame("09:07:59", 1.0), frame("09:08:30", 22500.5),
                                                          frame("09:14:59", 22510.25), frame("09:15:00", 22600.0)]) + "\n")
    assert q01.official_open(tmp_path) == (22510.25, "raw_frames_preopen")
    assert q01.official_open(tmp_path / "missing") == (None, "OPEN_MISSING")
