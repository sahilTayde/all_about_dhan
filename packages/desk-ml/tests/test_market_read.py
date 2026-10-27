"""market_read: real 2026-10-12 NIFTY tape bars, DATA_MISSING discipline, live hook, timing, log-only."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from desk_ml import market_read as mr

FIX = json.loads((Path(__file__).parent / "fixtures" / "market_read_2026-10-12.json").read_text())
BARS = [tuple(b) for b in FIX["bars_2026_10_12"]]
DAY = "2026-10-12"


def test_day_context_from_calendar_and_daily():
    ctx = mr.day_context(DAY, "NIFTY", FIX)
    assert (ctx["pdh"], ctx["pdl"], ctx["pdc"]) == (22580.75, 22294.75, 22520.45)  # prior trading day Oct 9
    assert (ctx["wk_hi"], ctx["wk_lo"]) == (22776.1, 22179.9)  # week of Oct 5 (Oct 2 holiday week not used)
    assert ctx["expiry"] == 0 and mr.is_expiry("2026-10-13", "NIFTY") == 1
    assert 0 <= ctx["vixp"] <= 1 and round(ctx["vch"], 4) == -0.0589


def test_partial_prior_day_is_data_missing():
    d = json.loads(json.dumps(FIX))
    d["NIFTY"]["2026-10-09"][4] = True  # partial tape
    ctx = mr.day_context(DAY, "NIFTY", d)
    assert ctx["pdh"] == ctx["pdl"] == ctx["pdc"] == mr.DM
    assert ctx["wk_hi"] == mr.DM


def test_compute_real_tape_and_missing_inputs():
    ctx = mr.day_context(DAY, "NIFTY", FIX)
    r = mr.compute(BARS, ctx, None, None, None, day=DAY)
    assert r["day_type"] == "GAP_OPEN"  # open 22611.05 vs pdc 22520.45 = +0.40%
    assert (r["or_hi"], r["or_lo"]) == (22650.25, 22512.5)
    assert r["spot"] == 22363.35 and r["log_only"] is True
    for k in ("vix", "vix_chg", "crude_chg", "gold_chg", "usdinr_chg", "pcr", "maxpain", "atm_iv",
              "depth_imb", "bnf_agree", "heavy_breadth", "gift_global"):
        assert r[k] == mr.DM and k in r["missing"]
    early = mr.compute(BARS[:10], ctx, day=DAY)
    assert early["day_type"] == "PENDING" and early["or_hi"] == mr.DM
    # no prior-day info at all -> never guessed
    bare = mr.compute(BARS, {}, day=DAY)
    assert bare["day_type"] == mr.DM and bare["pdh"] == mr.DM


def test_cross_inputs_and_structure():
    cross = {"INDIAVIX": {"last": 15.0, "prev_close": 14.0}, "CRUDEOIL": {"open": 100.0, "last": 101.0},
             "BANKNIFTY": {"last": 50000.0, "last5": 50100.0}, "SBIN": {"open": 800.0, "last": 790.0},
             "TCS": {"open": 3000.0, "last": 3010.0}}
    r = mr.compute(BARS, {}, cross, {"pcr": 0.91, "atm_iv": 12.3, "maxpain": None}, (300.0, 100.0), day=DAY)
    assert r["vix_chg"] == round((15 / 14 - 1) * 100, 3) and r["crude_chg"] == 1.0
    assert r["heavy_breadth"] == {"up": 1, "down": 1, "of": 2}
    assert r["depth_imb"] == 0.5 and r["pcr"] == 0.91 and r["maxpain"] == mr.DM
    tri = [0, 1, 2, 3, 2, 1]
    up = [("09:%02d" % i, 0, 100 + i + 4 * tri[i % 6], 98 + i + 4 * tri[i % 6], 99 + i) for i in range(15, 45)]
    hs, ls = mr.swings(up)
    assert mr.trend_structure(hs, ls) == ("UP", "HH_HL")


def test_timing_under_200ms():
    ctx = mr.day_context(DAY, "NIFTY", FIX)
    worst = 0.0
    for i in range(1, len(BARS) + 1, 7):
        t = time.perf_counter()
        mr.compute(BARS[:i], ctx, day=DAY)
        worst = max(worst, (time.perf_counter() - t) * 1000)
    assert worst < 200


class Snap(dict):
    def to_dict(self):
        return dict(self)


def test_live_logger_one_line_per_closed_minute(tmp_path, monkeypatch):
    daily = tmp_path / "daily.json"
    daily.write_text(json.dumps(FIX))
    monkeypatch.setenv("MARKET_READ_DAILY", str(daily))
    cross = tmp_path / "cross" / "INDIAVIX"
    cross.mkdir(parents=True)
    (cross / f"{DAY}.jsonl").write_text(json.dumps({"ts": "x", "o": 14.4, "c": 14.6, "prev_close": 14.38}) + "\n")
    monkeypatch.setenv("MARKET_READ_CROSS_TAPE", str(tmp_path / "cross"))
    lg = mr.LiveLogger(tmp_path, underlyings=("NIFTY",))
    t = lambda h, m, s: datetime(2026, 10, 12, h, m, s, tzinfo=mr.IST)
    out = []
    for (m, o, h, l, c) in BARS[:20]:
        hh, mm = map(int, m.split(":"))
        for s, px in ((1, o), (20, h), (40, l), (59, c)):
            out += lg.on_tick([Snap(underlying="NIFTY", index_ltp=px, index_source="dhan_live")], t(hh, mm, s))
    out += lg.on_tick([Snap(underlying="NIFTY", index_ltp=None)], t(9, 35, 0))
    assert len(out) == 20 and out[-1]["ts"].endswith("09:34:00+05:30")
    assert out[-1]["vix"] == 14.6 and out[-1]["vix_chg"] != mr.DM
    lines = (tmp_path / "data" / "market_read" / DAY / "market_read.jsonl").read_text().splitlines()
    assert len(lines) == 20
    # a broken snap never raises
    assert lg.on_tick([object()], t(9, 36, 0)) == []
