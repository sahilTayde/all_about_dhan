"""Fix 8: paper fills walk recorded book levels for the order qty (SENSEX 200 qty exceeded the top level
92% of the time on 2026-10-12), instead of top-of-book."""

from __future__ import annotations

import json
from pathlib import Path

from desk_ml import research_rules as rr

from test_research_rules_v2_fill import DAY, _ts, _write_v2


def test_walk_book_vwap_and_flags() -> None:
    asks = [[427.5, 60], [428.0, 100], [429.0, 500]]
    px, flag = rr.walk_book(asks, 200)
    assert flag == "DEPTH_WALK" and px == round((60 * 427.5 + 100 * 428.0 + 40 * 429.0) / 200, 4)
    assert rr.walk_book(asks, 50) == (427.5, None)
    px, flag = rr.walk_book([[10.0, 50]], 200)
    assert flag == "DEPTH_SHORT" and px == 10.0
    assert rr.walk_book([], 200) == (None, None)


def test_strike_quote_uses_levels_when_qty_given() -> None:
    bar = {"wings": {"71800": {"pe_ask": 427.5, "pe_bid": 427.0,
                               "pe_ask_levels": [[427.5, 60], [428.5, 500]], "pe_bid_levels": [[427.0, 40], [426.0, 500]]}}}
    assert rr.strike_quote(bar, "PE", 71800.0, "ask") == (427.5, None)          # no qty: top of book
    ask, f = rr.strike_quote(bar, "PE", 71800.0, "ask", qty=200)
    bid, g = rr.strike_quote(bar, "PE", 71800.0, "bid", qty=200)
    assert ask > 427.5 and bid < 427.0 and f == g == "DEPTH_WALK"


def test_v2_loader_attaches_option_levels(tmp_path: Path) -> None:
    rr._V2_STATE.clear()
    _write_v2(tmp_path, ["10:31"])
    dq = tmp_path / "data" / "tape" / "v2" / DAY / "depth_quotes.jsonl"
    with dq.open("a") as fh:
        fh.write(json.dumps({"payload": {"instrument_id": "NSE_FNO:NIFTY:2026-10-13:25000:CE",
                                         "levels": {"bid": [[120.0, 65], [119.5, 650]], "ask": [[121.0, 65], [121.5, 650]]},
                                         "exchange_ts": _ts("10:31", 40)}, "timestamp": _ts("10:31", 40)}) + "\n")
    bar = rr.load_v2_minutes(tmp_path, "NIFTY", DAY)["10:31"]
    assert bar["wings"]["25000"]["ce_ask_levels"][1] == [121.5, 650]
    px, flag = rr.strike_quote(bar, "CE", 25000.0, "ask", qty=650)
    assert flag == "DEPTH_WALK" and 121.0 < px < 121.5
