"""2026-10-12 late time exits: the H20 TIME exit is decided by the wall clock, not by the latest tape
minute, and books the last known bid when the tape lags. Cases from the 2026-10-12 session, when the
book's prices lagged the tape by ~3.3 min and the live loop (commit 4aa8778) waited for the tape."""

from __future__ import annotations

from desk_ml import research_rules as rr


def _bars(und_strike: float, side: str, start: str, end: str, px: float) -> dict:
    out = {}
    m = start
    while m <= end:
        out[m] = {"hhmm": m, "ts": 0, "atm": und_strike,
                  "wings": {str(int(und_strike)): {f"{side.lower()}_bid": px, f"{side.lower()}_ask": px + 0.5}}}
        px += 0.25
        m = rr.mplus(m, 1)
    return out


def _check(strike, side, entry_min, entry, tape_last, wall, want_exit):
    bars = _bars(strike, side, entry_min, tape_last, entry)
    minutes = list(bars)
    spec = rr.mplus(entry_min, 20)
    assert spec == want_exit
    # tape clock alone (old behaviour): still open because the tape has not reached the exit
    assert rr._pick_exit(bars, minutes, side=side, strike=strike, spec_exit=spec,
                         entry_min=entry_min, last_hhmm=tape_last) is None
    # wall clock: closed, at the last known bid at/before the exit, never left open
    pick = rr._pick_exit(bars, minutes, side=side, strike=strike, spec_exit=spec,
                         entry_min=entry_min, last_hhmm=tape_last, now_hhmm=wall)
    assert pick is not None
    m, px, _flag = pick
    assert m == min(tape_last, spec)
    assert px == bars[m]["wings"][str(int(strike))][f"{side.lower()}_bid"]
    assert m <= spec


def test_r02_sensex_71800_pe_closes_at_1437_by_wall_clock() -> None:
    # shadow R02 SENSEX 71800 PE 200 qty in 427.5 at 14:17 IST; was open at 14:40 (tape ~3.3 min behind)
    _check(71800.0, "PE", "14:17", 427.5, tape_last="14:36", wall="14:40", want_exit="14:37")


def test_r01_pdiv_nifty_22350_pe_closes_at_1449_by_wall_clock() -> None:
    # shadow R01_PDIV NIFTY 22350 PE 650 qty in 91.1 at 14:29 IST; was open at 14:53
    _check(22350.0, "PE", "14:29", 91.1, tape_last="14:47", wall="14:53", want_exit="14:49")


def test_not_closed_before_wall_clock_reaches_exit() -> None:
    bars = _bars(22350.0, "PE", "14:29", "14:40", 91.1)
    assert rr._pick_exit(bars, list(bars), side="PE", strike=22350.0, spec_exit="14:49",
                         entry_min="14:29", last_hhmm="14:40", now_hhmm="14:48") is None


def test_replay_underlying_closes_overdue_trade_with_wall_clock() -> None:
    rule = {"rule_id": "T", "family": "X", "hold_min": 20, "source_config": "T"}
    bars = _bars(71800.0, "PE", "14:17", "14:36", 427.5)
    import desk_ml.research_rules as m
    orig_sig, orig_allowed = m.signal, m.allowed
    try:
        m.signal = lambda rule, bars, t, underlying: "PE" if t == "14:16" else None
        m.allowed = lambda minutes, t: True
        bars = {"14:16": {**bars["14:17"], "hhmm": "14:16"}, **bars}
        o, c = m.replay_underlying(bars, underlying="SENSEX", day="2026-10-12", rules=[rule])
        assert len(o) == 1 and not c  # tape clock: stays open (the 2026-10-12 bug)
        o, c = m.replay_underlying(bars, underlying="SENSEX", day="2026-10-12", rules=[rule], now_hhmm="14:40")
        assert not o and len(c) == 1
        assert c[0]["spec_exit_min"] == "14:37" and c[0]["exit_min"] <= "14:37"
    finally:
        m.signal, m.allowed = orig_sig, orig_allowed
