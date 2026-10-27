"""Board 'Today' P&L counts only traded desk rows; shadow/refused/old-book rows are reported separately.
2026-10-12: 3 old-book MIX-DEFAULT-BUY rows (-83,417.07) were counted in Today."""

from __future__ import annotations

from api import ui_feed as uf

DAY = "2026-10-12"


def _r(tid, net, **kw):
    return {"trade_id": tid, "day": DAY, "realized_pnl_inr": net, "opened_ts": hash(tid) % 10**6,
            "underlying": "NIFTY", "side": "PE", **kw}


def test_old_book_and_shadow_rows_not_in_desk_net() -> None:
    rows = [_r("o1", -27117.61, book_id="MIX-DEFAULT-BUY"), _r("o2", -28399.81, book_id="MIX-DEFAULT-BUY"),
            _r("o3", -27899.65, book_id="MIX-DEFAULT-BUY"),
            _r("d1", 1200.0, book_id="R01_PDIV_5_ALL_H20", desk_status="TRADED", shadow=False),
            _r("s1", -5000.0, book_id="R02", desk_status="SHADOW_PARKED", shadow=True),
            _r("x1", -700.0, book_id="R01_B3A_VOL", desk_status="DUP_SAME_CONTRACT", shadow=True)]
    (d,) = uf.day_summaries(rows)
    assert d["n"] == 1 and d["net"] == 1200.0
    assert d["shadow"]["n"] == 5
    assert d["shadow"]["by_book"]["MIX-DEFAULT-BUY"] == {"n": 3, "net": -83417.07}
    t = uf._today_split([d], DAY)
    assert t["desk_net_inr"] == 1200.0 and t["shadow_trades"] == 5


def test_old_book_before_cutoff_still_desk() -> None:
    (d,) = uf.day_summaries([{**_r("o", 100.0, book_id="MIX-DEFAULT-BUY"), "day": "2026-10-09"}])
    assert d["net"] == 100.0 and d["shadow"]["n"] == 0
