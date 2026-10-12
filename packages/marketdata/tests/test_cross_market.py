"""Cross-market recorder: ids from a real scrip-master excerpt, minute bars from packets, tape layout."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from marketdata.cross_market import IST, CrossTape, MinuteBars, latest, resolve

FIX = Path(__file__).parent / "fixtures" / "cross_scrip_sample.csv"


def test_resolve_from_scrip_master():
    insts, missing = resolve(FIX.read_text(), date(2026, 10, 12))
    ids = {i.name: (i.segment, i.security_id, i.symbol) for i in insts}
    assert ids["INDIAVIX"] == ("IDX_I", "21", "INDIA VIX")
    assert ids["BANKNIFTY"][:2] == ("IDX_I", "25")
    assert ids["SBIN"][:2] == ("NSE_EQ", "3045")
    assert ids["CRUDEOIL"] == ("MCX_COMM", "569900", "CRUDEOIL-19Oct2026-FUT")  # front month, not CRUDEOILM
    assert ids["GOLD"][1] == "495213"
    assert missing == ["USDINR"]  # master lists no unexpired USDINR future: skipped, never guessed
    assert "NIFTY PVT BANK" not in {i.symbol for i in insts}
    # after crude's Oct expiry the next month is picked
    insts2, _ = resolve(FIX.read_text(), date(2026, 10, 20))
    assert {i.name: i.security_id for i in insts2}["CRUDEOIL"] == "573422"


def _pkt(sid, ltp=None, kind="quote", **f):
    fields = dict(f)
    if ltp is not None:
        fields["ltp"] = ltp
    return {"kind": kind, "security_id": sid, "fields": fields}


def test_minute_bars_and_tape(tmp_path):
    insts, _ = resolve(FIX.read_text(), date(2026, 10, 12))
    mb = MinuteBars(insts)
    t = lambda h, m, s: datetime(2026, 10, 12, h, m, s, tzinfo=IST)
    rows = []
    rows += mb.on_packet(_pkt("21", kind="prev_close", prev_close=14.38), t(9, 15, 0))
    rows += mb.on_packet(_pkt("21", 14.5), t(9, 15, 1))
    rows += mb.on_packet(_pkt("21", 14.9), t(9, 15, 30))
    rows += mb.on_packet(_pkt("21", 14.2), t(9, 15, 59))
    rows += mb.on_packet(_pkt("999999", 1.0), t(9, 15, 59))  # unknown id ignored
    rows += mb.on_packet(_pkt("3045", 800.0, volume=1000), t(9, 15, 10))
    assert rows == []
    rows += mb.on_packet(_pkt("21", 14.6), t(9, 16, 2))  # closes 09:15
    vix = [r for r in rows if r["name"] == "INDIAVIX"][0]
    assert (vix["o"], vix["h"], vix["l"], vix["c"], vix["ticks"]) == (14.5, 14.9, 14.2, 14.2, 3)
    assert vix["prev_close"] == 14.38 and vix["ts"] == "2026-10-12T09:15:00+05:30"
    sbin = [r for r in rows if r["name"] == "SBIN"][0]
    assert sbin["volume"] == 1000
    rows += mb.roll(t(9, 30, 0))
    tape = CrossTape(tmp_path)
    tape.write(rows)
    assert json.loads((tmp_path / "SCHEMA.json").read_text())["version"] == 1
    assert latest(tmp_path, "INDIAVIX", "2026-10-12")["c"] == 14.6
    assert latest(tmp_path, "CRUDEOIL", "2026-10-12") is None  # no packet -> no row (gap, not carried)
