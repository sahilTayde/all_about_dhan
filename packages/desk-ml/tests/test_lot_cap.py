"""Hard 10-lot cap (NIFTY qty <= 650, SENSEX qty <= 200) at the single booking point, regardless of book.
2026-10-12: MIX-DEFAULT-BUY fired 25 lots (1625 / 500 qty) at 09:52 and 10:18 IST."""

from __future__ import annotations

from desk_ml import paper_scalp as ps


def _pos(und, lot, lots, book="MIX-DEFAULT-BUY"):
    return ps.OpenPaper(book_id=book, underlying=und, side="PE", trade_id="t", entry=100.0, stop=60.0,
                        target=150.0, atm_strike=22350.0, opened_ts=0, opened_bar=0, strike_source="x",
                        lot_size=lot, lots=lots, qty=lot * lots, notional_inr=100.0 * lot * lots)


def test_25_lot_rows_are_clamped_to_10() -> None:
    n = ps.enforce_lot_cap(_pos("NIFTY", 65, 25))
    s = ps.enforce_lot_cap(_pos("SENSEX", 20, 25))
    assert (n.lots, n.qty, n.notional_inr) == (10, 650, 65000.0)
    assert (s.lots, s.qty) == (10, 200)


def test_qty_cap_holds_if_lot_size_changes() -> None:
    assert ps.enforce_lot_cap(_pos("NIFTY", 75, 10)).qty <= 650
    assert ps.enforce_lot_cap(_pos("SENSEX", 25, 10)).qty <= 200


def test_within_cap_unchanged_and_never_sized_up() -> None:
    p = ps.enforce_lot_cap(_pos("NIFTY", 65, 4, book="R01"))
    assert (p.lots, p.qty) == (4, 260)


def test_commit_open_applies_cap() -> None:
    class E:
        opens = {}
        root = None
        def bump_regime_book(self, *a, **k):
            pass
    e = E()
    pos = _pos("NIFTY", 65, 25)
    pos.index_regime = None
    try:
        ps._commit_open(e, pos)
    except Exception:
        pass
    assert e.opens[("MIX-DEFAULT-BUY", "NIFTY")].qty == 650


def test_total_open_qty_per_underlying_across_books() -> None:
    class E:
        def __init__(self):
            self.opens = {}; self.root = None; self.skips = []
        def bump_regime_book(self, *a, **k):
            pass
        def mark_skip(self, *a, **k):
            self.skips.append(a)
    e = E()
    first = _pos("NIFTY", 65, 10, book="R01"); first.index_regime = None
    e.opens[("R01", "NIFTY")] = first
    second = _pos("NIFTY", 65, 10, book="R01_B3A_VOL"); second.index_regime = None
    ps._commit_open(e, second)
    assert ("R01_B3A_VOL", "NIFTY") not in e.opens and e.skips
    assert sum(o.qty for o in e.opens.values()) == 650
