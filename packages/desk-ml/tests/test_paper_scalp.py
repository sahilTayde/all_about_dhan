"""Parallel paper scalpers: independent books, feasible scalp exits, paper hit rate."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from desk_ml.features import Triple
from desk_ml.paper_scalp import (
    BookEngine,
    LIVE_BOOKS,
    OpenPaper,
    SIDEWAYS_HOLD,
    classify_index_regime,
    feasibility_long,
    mark_to_market,
    paper_hit_rate,
    propose_levels,
    quote_for_side,
    replay_paper_scalp,
    step_underlying,
)
from desk_ml.tape import merge_wing_quotes
from warehouse.feasibility import evaluate_long_premium

IST = timezone(timedelta(hours=5, minutes=30))


def _ts(i: int) -> int:
    return int(datetime(2026, 9, 10, 10, 0, tzinfo=IST).timestamp()) + i * 60


def _triples(*, n: int = 80, trend: float = 8.0) -> list[Triple]:
    out: list[Triple] = []
    idx, ce, pe = 25000.0, 120.0, 110.0
    for i in range(n):
        idx += trend
        ce = max(8.0, ce + trend * 0.15)
        pe = max(8.0, pe - trend * 0.12)
        out.append(Triple(ts=_ts(i), idx_close=idx, ce_close=ce, pe_close=pe))
    return out


def _chop_triples(*, n: int = 80) -> list[Triple]:
    out: list[Triple] = []
    idx, ce, pe = 25000.0, 120.0, 110.0
    for i in range(n):
        idx += 4.0 if i % 2 == 0 else -4.0
        ce = max(8.0, 120.0 + (2.0 if i % 2 == 0 else -2.0))
        pe = max(8.0, 110.0 + (-2.0 if i % 2 == 0 else 2.0))
        out.append(Triple(ts=_ts(i), idx_close=idx, ce_close=ce, pe_close=pe))
    return out


def test_classify_index_regime_trend_vs_sideways() -> None:
    trend = [25000.0 + i * 8.0 for i in range(40)]
    chop = [25000.0 + (4.0 if i % 2 == 0 else -4.0) for i in range(40)]
    t = classify_index_regime(trend)
    s = classify_index_regime(chop)
    assert t["regime"] == "TREND"
    assert t["direction"] == "UP"
    assert s["regime"] == "SIDEWAYS"
    short = classify_index_regime([25000.0, 25001.0])
    assert short["regime"] == "UNKNOWN"


def test_sideways_skips_new_opens_not_dealer_yaml() -> None:
    triples = _chop_triples()
    engine = BookEngine()
    step_underlying(
        engine,
        underlying="NIFTY",
        triples=triples,
        i=40,
        ml001_hold=False,
        ml002_hold=False,
        follow_gap=False,
        logit={"side": "CE", "status": "OK"},
        logit_xr={"side": "CE", "status": "OK"},
        ml1={"status": "OK", "take": True},
        tv_side="CE",
        deny_model_signals=False,
    )
    assert engine.last_regime["NIFTY"]["regime"] == "SIDEWAYS"
    for book in ("MIX-DEFAULT-BUY", "MIX-ML-LOGIT", "MIX-TV-EP-024"):
        assert engine.has_open(book, "NIFTY") is False
    assert any(s.get("reason") == SIDEWAYS_HOLD and s.get("book_id") == "MIX-DEFAULT-BUY" for s in engine.skips)


def test_sideways_still_flattens_open_ticket() -> None:
    from desk_ml.paper_scalp import OpenPaper, mark_to_market

    triples = _chop_triples()
    engine = BookEngine()
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="already-open",
        entry=120.0,
        stop=80.0,
        target=160.0,
        atm_strike=25000.0,
        opened_ts=int(__import__("datetime").datetime(2026, 9, 10, 15, 0, tzinfo=IST).timestamp()) - 60,
        opened_bar=49,
        strike_source="TEST",
        limit_price=120.0,
        filled=True,
        index_regime="TREND",
    )
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos
    engine.equity["MIX-DEFAULT-BUY"] = 10000.0
    late = int(__import__("datetime").datetime(2026, 9, 10, 15, 1, tzinfo=IST).timestamp())
    tick = Triple(ts=late, idx_close=25000.0, ce_close=118.0, pe_close=110.0)
    mark_to_market(engine, tick, "NIFTY", 50)
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert engine.closed and engine.closed[0]["exit_reason"] == "FLATTEN_1500"


def test_paper_hit_rate_from_closed_pnl() -> None:
    assert paper_hit_rate([]) is None
    assert paper_hit_rate([1.0, -2.0, 3.0, 0.0]) == 0.5
    assert paper_hit_rate([-1.0, -1.0]) == 0.0


def test_fantasy_150_96_250_killed() -> None:
    dec = evaluate_long_premium(
        entry=150.0,
        stop=96.0,
        target=250.0,
        typical_premium_range=20.0,
    )
    assert dec.ok is False
    assert dec.reason_code == "TARGET_FEASIBILITY_FAIL"
    wrapped = feasibility_long(entry=150.0, stop=96.0, target=250.0, typical_range=20.0)
    assert wrapped["ok"] is False
    assert wrapped["reason_code"] == "TARGET_FEASIBILITY_FAIL"


def test_propose_levels_uses_path_not_hero_target() -> None:
    entry = 100.0
    path = [98.0, 99.0, 100.0, 101.0, 102.0, 103.0]
    levels = propose_levels(entry, path)
    assert levels["ok"] is True
    assert levels["stop"] < levels["entry"] < levels["target"]
    span = levels["target"] - levels["entry"]
    assert span <= 3.0 * levels["typical_premium_range"] + 1e-9
    assert levels["limit_price"] < levels["entry"]


def test_allocate_desk_capital_skips_greeks_book() -> None:
    from desk_ml.paper_scalp import allocate_desk_capital, LIVE_BOOKS

    plan = allocate_desk_capital(tradable=[b for b in LIVE_BOOKS if b != "MIX-ML-GREEKS"])
    assert plan["desk_capital_inr"] == 70000.0
    assert plan["per_book"]["MIX-ML-GREEKS"] == 0.0
    active = [b for b in LIVE_BOOKS if b != "MIX-ML-GREEKS"]
    assert sum(plan["per_book"][b] for b in active) == 70000.0
    assert plan["per_book"][active[0]] == 10000.0


def test_trend_up_kills_new_pe_not_a_strat() -> None:
    triples = _triples(n=50, trend=8.0)
    engine = BookEngine()
    step_underlying(
        engine,
        underlying="NIFTY",
        triples=triples,
        i=40,
        ml001_hold=False,
        ml002_hold=False,
        follow_gap=False,
        logit={"side": "PE", "status": "OK"},
        logit_xr={"side": "PE", "status": "OK"},
        ml1={"status": "OK", "take": True},
        tv_side="PE",
        deny_model_signals=True,
    )
    assert engine.last_regime["NIFTY"]["regime"] == "TREND"
    assert engine.last_regime["NIFTY"]["direction"] == "UP"
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is False
    assert any(s.get("reason") == "TREND_UP_KILL_PE" for s in engine.skips)


def test_sleep_with_beats_rewrites_without_dhan_poll() -> None:
    from desk_ml.paper_scalp import sleep_with_beats

    slept: list[float] = []
    beats: list[float] = []

    def _sleep(sec: float) -> None:
        slept.append(sec)

    def _beat(remaining: float) -> None:
        beats.append(remaining)

    out = sleep_with_beats(12.0, beat_seconds=5.0, sleep_fn=_sleep, on_beat=_beat)
    assert out == "slept"
    assert slept == [5.0, 5.0, 2.0]
    assert len(beats) == 3


def test_greeks_cancel_filled_when_delta_dies() -> None:
    from desk_ml.paper_scalp import OpenPaper, _exit_reason

    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="greeks-die",
        entry=100.0,
        stop=80.0,
        target=130.0,
        atm_strike=23200.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="TEST",
        limit_price=98.8,
        filled=True,
    )
    reason = _exit_reason(
        pos,
        101.0,
        _ts(1),
        2,
        live_greeks={"delta": 0.22, "iv": 16.0, "theta": -2.0, "gamma": 0.002},
    )
    assert reason == "CANCEL_GREEKS_DELTA_TOO_LOW"


def test_ml001_hold_does_not_block_dealer() -> None:
    triples = _triples()
    engine = BookEngine()
    i = 40
    step_underlying(
        engine,
        underlying="NIFTY",
        triples=triples,
        i=i,
        ml001_hold=True,
        ml002_hold=False,
        follow_gap=True,
        logit={"side": None, "status": "DATA_INSUFFICIENT", "reason": "thin"},
        logit_xr={"side": None, "status": "SKIP", "reason": "thin"},
        ml1={"status": "DATA_INSUFFICIENT", "reason": "no labels"},
        tv_side="CE",
        deny_model_signals=True,
    )
    dealer_open = engine.has_open("MIX-DEFAULT-BUY", "NIFTY")
    ml001_open = engine.has_open("ML-001", "NIFTY")
    tv_open = engine.has_open("MIX-TV-EP-024", "NIFTY")
    assert dealer_open is True
    assert ml001_open is False
    assert tv_open is True
    skip_books = {s["book_id"] for s in engine.skips if s["book_id"] in {"ML-001", "ML-002"}}
    assert "ML-001" in skip_books


def test_one_open_per_book_underlying() -> None:
    triples = _triples()
    engine = BookEngine()
    for i in (30, 31, 32):
        step_underlying(
            engine,
            underlying="NIFTY",
            triples=triples,
            i=i,
            ml001_hold=False,
            ml002_hold=False,
            follow_gap=False,
            logit={"side": None, "status": "SKIP"},
            logit_xr={"side": None, "status": "SKIP"},
            ml1={"status": "DATA_INSUFFICIENT", "reason": "no labels"},
            tv_side="CE",
        )
    assert sum(1 for (b, u) in engine.opens if b == "MIX-DEFAULT-BUY" and u == "NIFTY") <= 1
    assert sum(1 for (b, u) in engine.opens if b == "MIX-TV-EP-024" and u == "NIFTY") <= 1


def test_scalp_time_exit_closes_premium_pnl() -> None:
    triples = _triples(n=50)
    engine = BookEngine()
    for i in range(20, 40):
        step_underlying(
            engine,
            underlying="NIFTY",
            triples=triples,
            i=i,
            ml001_hold=True,
            ml002_hold=True,
            follow_gap=True,
            logit={"side": None, "status": "SKIP"},
            logit_xr={"side": None, "status": "SKIP"},
            ml1={"status": "DATA_INSUFFICIENT", "reason": "no labels"},
            tv_side="CE",
        )
    closed_tv = [c for c in engine.closed if c["book_id"] == "MIX-TV-EP-024"]
    assert closed_tv
    reasons = {c["exit_reason"] for c in closed_tv}
    assert reasons & {
        "TIME",
        "STOP",
        "TARGET",
        "FLATTEN_1500",
        "CANCEL_STRIKE_ROLL",
        "CANCEL_ADVERSE",
        "CANCEL_THESIS",
        "CANCEL_UNFILLED_AWAY",
        "CANCEL_UNFILLED_TIMEOUT",
        "CANCEL_UNFILLED_INDEX",
        "CANCEL_UNFILLED_THESIS",
        "CANCEL_UNFILLED_FLAT",
    }
    assert all(c["realized_pnl"] is not None for c in closed_tv)
    assert all("won" in c for c in closed_tv)
    assert all(c.get("atm_strike") is not None for c in closed_tv)
    assert all("stop" in c and "target" in c for c in closed_tv)


def test_replay_parallel_books_no_promote(tmp_path) -> None:
    triples = _triples(n=90)
    board = replay_paper_scalp(
        root=tmp_path,
        underlyings=("NIFTY",),
        triples_by_und={"NIFTY": triples},
        write=False,
    )
    assert board["ok"] is True
    assert board["promote"] is False
    assert board["independent_books"] is True
    ids = {m["model_id"] for m in board["models"]}
    assert ids == set(LIVE_BOOKS)
    assert board["research_ready_for_programming"] is False
    assert board["execution"] == "refused"
    assert board["starting_desk_inr"] == 70000.0
    assert board["capital_plan"]["skipped"] == ["MIX-ML-GREEKS"]
    assert board["win_rate_kind"] == "paper_closed_net_inr_gt_0_after_groww_stt"
    assert "win_rate_gross_pct" in board
    assert "book_rank" in board
    assert "today" in board
    assert board["cost_model"]["name"] == "GROWW_FO_20_PLUS_STT_015"
    if board["n_closed"]:
        assert board["win_rate"] is not None
        assert 0.0 <= float(board["win_rate"]) <= 1.0
    ml1 = next(m for m in board["models"] if m["model_id"] == "ML-1")
    lb = board["leaderboard"]
    if lb:
        assert all(row.get("win_rate") is None or 0.0 <= float(row["win_rate"]) <= 1.0 for row in lb)


def test_books_do_not_share_veto_on_banknifty() -> None:
    a = _triples(n=40, trend=6.0)
    b = _triples(n=40, trend=-6.0)
    engine = BookEngine()
    step_underlying(
        engine,
        underlying="NIFTY",
        triples=a,
        i=25,
        ml001_hold=True,
        ml002_hold=False,
        follow_gap=False,
        logit={"side": "CE", "status": "OK"},
        logit_xr={"side": None, "status": "SKIP"},
        ml1={"status": "DATA_INSUFFICIENT", "reason": "no labels"},
        tv_side=None,
        deny_model_signals=True,
    )
    step_underlying(
        engine,
        underlying="BANKNIFTY",
        triples=b,
        i=25,
        ml001_hold=False,
        ml002_hold=True,
        follow_gap=False,
        logit={"side": "PE", "status": "OK"},
        logit_xr={"side": None, "status": "SKIP"},
        ml1={"status": "DATA_INSUFFICIENT", "reason": "no labels"},
        tv_side="PE",
        deny_model_signals=True,
    )
    # Opposite underlyings stay independent even if one overlay HOLDs.
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is True
    assert engine.has_open("MIX-ML-LOGIT", "BANKNIFTY") is True
    assert engine.has_open("ML-001", "NIFTY") is False
    assert engine.has_open("ML-002", "BANKNIFTY") is False


def test_live_session_filters_other_ist_days_and_keeps_open() -> None:
    today = _triples(n=40)
    yesterday = [
        Triple(
            ts=int(datetime(2026, 9, 15, 10, 0, tzinfo=IST).timestamp()) + i * 60,
            idx_close=24000 + i,
            ce_close=90 + i * 0.2,
            pe_close=80,
        )
        for i in range(40)
    ]
    board = replay_paper_scalp(
        underlyings=("NIFTY",),
        triples_by_und={"NIFTY": yesterday + today},
        write=False,
        live_session=True,
        session_ist_date="2026-09-10",
        deny_model_signals=False,
    )
    assert board["live_session"] is True
    assert board["session_ist_date"] == "2026-09-10"
    assert board["overall_pnl_inr"] is not None
    n_today = 40
    # Yesterday bars must not inflate closed count the way full jsonl did.
    assert board["n_closed"] < 400
    steps = board["steps"]["NIFTY"]
    assert steps["n_triples"] == n_today
    if board["n_open"]:
        assert all(t.get("status") in {"OPEN_PAPER", "WORKING_LIMIT"} for t in board["open_trades"])
        assert all(t.get("side") in {"CE", "PE"} for t in board["open_trades"])
        assert all(t.get("atm_strike") is not None for t in board["open_trades"])
    for t in board["closed_trades"]:
        assert t.get("result") in {"SUCCESS", "LOSS", "CANCELLED"}
        assert t.get("status") == "CLOSED_PAPER"
    if board["n_losses"]:
        assert board["mistakes"]
        assert board["money_lost_inr"] <= 0


def test_nudge_waits_for_eight_closes() -> None:
    from desk_ml.paper_scalp import DEFAULT_PAPER_PARAMS, nudge_paper_params

    params, notes = nudge_paper_params([], DEFAULT_PAPER_PARAMS)
    assert params["stop_frac"] == DEFAULT_PAPER_PARAMS["stop_frac"]
    assert any("≥8" in n or ">=" in n or "8" in n for n in notes)


def test_cancel_when_sensex_ce_dumps_under_entry() -> None:
    from desk_ml.paper_scalp import OpenPaper, _exit_reason

    pos = OpenPaper(
        book_id="MIX-ML-LOGIT",
        underlying="SENSEX",
        side="CE",
        trade_id="paper-sensex-ce",
        entry=297.45,
        stop=240.0,
        target=325.0,
        atm_strike=74300.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="TEST",
        limit_price=297.45,
    )
    # Last ATM print recovered; 74300 CE already printed 258 in the minute.
    reason = _exit_reason(
        pos, 300.0, _ts(2), 3, side_low=258.0, atm_strike=74300.0
    )
    assert reason == "CANCEL_ADVERSE"


def test_cancel_thesis_when_dealer_flips_confirm() -> None:
    from desk_ml.paper_scalp import OpenPaper, _exit_reason

    pos = OpenPaper(
        book_id="MIX-ML-LOGIT",
        underlying="SENSEX",
        side="CE",
        trade_id="paper-sensex-ce-thesis",
        entry=297.45,
        stop=280.5,
        target=325.0,
        atm_strike=74300.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="TEST",
        limit_price=297.45,
    )
    reason = _exit_reason(
        pos, 290.0, _ts(2), 3, atm_strike=74300.0, dealer_verdict="BUY_PE_CONFIRM"
    )
    assert reason == "CANCEL_THESIS"


def test_cancel_when_atm_strike_rolls() -> None:
    from desk_ml.paper_scalp import OpenPaper, _exit_reason

    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="SENSEX",
        side="CE",
        trade_id="paper-sensex-roll",
        entry=297.45,
        stop=280.5,
        target=325.0,
        atm_strike=74300.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="TEST",
        limit_price=297.45,
    )
    reason = _exit_reason(pos, 290.0, _ts(2), 3, atm_strike=74400.0)
    assert reason == "CANCEL_STRIKE_ROLL"


def test_itm_wing_is_100pts_not_atm() -> None:
    from desk_ml.paper_scalp import itm_wing_strikes

    assert itm_wing_strikes("SENSEX", 74300.0) == {"CE": 74200.0, "PE": 74400.0}
    assert itm_wing_strikes("NIFTY", 23250.0) == {"CE": 23150.0, "PE": 23350.0}


def test_open_uses_itm_quote_not_atm() -> None:
    from desk_ml.paper_scalp import BookEngine, _try_open

    tick = Triple(
        ts=_ts(10),
        idx_close=74300.0,
        ce_close=300.0,
        pe_close=305.0,
        atm_strike=74300.0,
        itm_ce_close=450.0,
        itm_pe_close=440.0,
        itm_ce_strike=74200.0,
        itm_pe_strike=74400.0,
        wing_quotes={
            "74200": {"ce": 450.0, "pe": 90.0},
            "74300": {"ce": 300.0, "pe": 305.0},
            "74400": {"ce": 90.0, "pe": 440.0},
        },
    )
    engine = BookEngine()
    _try_open(
        engine,
        book_id="MIX-DEFAULT-BUY",
        underlying="SENSEX",
        side="CE",
        tick=tick,
        ce_path=[450.0, 448.0, 452.0],
        pe_path=[440.0, 442.0],
        bar_i=10,
        strike=74300.0,
    )
    pos = engine.opens[("MIX-DEFAULT-BUY", "SENSEX")]
    assert pos.atm_strike == 74200.0
    assert pos.strike_source == "ITM_100"
    assert pos.entry == 450.0
    assert pos.limit_price == 444.6
    assert pos.limit_price < pos.entry
    assert pos.filled is False


def test_unfilled_limit_cancels_when_premium_runs_away() -> None:
    from desk_ml.paper_scalp import OpenPaper, _unfilled_reason

    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="wait-limit",
        entry=100.0,
        stop=80.0,
        target=130.0,
        atm_strike=23200.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="TEST",
        limit_price=100.0,
        filled=False,
        idx_at_open=23200.0,
    )
    assert _unfilled_reason(pos, 100.0, _ts(1), 2) == "FILL"
    assert _unfilled_reason(pos, 104.0, _ts(1), 2) == "CANCEL_UNFILLED_AWAY"
    assert _unfilled_reason(pos, 101.0, _ts(1), 2, live_delta=0.25) == "CANCEL_UNFILLED_DELTA"


def test_no_new_paper_after_1445_ist() -> None:
    from desk_ml.paper_scalp import BookEngine, _try_open

    late = int(datetime(2026, 9, 10, 14, 50, tzinfo=IST).timestamp())
    tick = Triple(ts=late, idx_close=23200.0, ce_close=80.0, pe_close=70.0)
    engine = BookEngine()
    _try_open(
        engine,
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        tick=tick,
        ce_path=[80.0],
        pe_path=[70.0],
        bar_i=10,
        strike=23200.0,
    )
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert any(s.get("reason") == "NO_NEW_AFTER_1445" for s in engine.skips)
    from desk_ml.paper_scalp import greeks_paper_adjust

    skip = greeks_paper_adjust(entry=100.0, stop_frac=0.40, target_frac=0.55, delta=0.25)
    assert skip["skip"] is True
    assert skip["reason"] == "DELTA_TOO_LOW"
    keep = greeks_paper_adjust(entry=100.0, stop_frac=0.40, target_frac=0.55, iv=30.0, theta=-8.0, gamma=0.02)
    assert keep["skip"] is False
    assert keep["stop_frac"] > 0.40
    assert keep["target_frac"] < 0.55


def test_pick_paper_strike_prefers_delta_band() -> None:
    from desk_ml.paper_scalp import pick_paper_strike

    tick = Triple(
        ts=_ts(10),
        idx_close=23250.0,
        ce_close=80.0,
        pe_close=70.0,
        atm_strike=23250.0,
        wing_quotes={
            "23150": {"ce": 140.0, "ce_delta": 0.62, "ce_theta": -7.0, "ce_iv": 16.0, "ce_gamma": 0.002},
            "23200": {"ce": 110.0, "ce_delta": 0.56, "ce_theta": -8.0, "ce_iv": 16.5, "ce_gamma": 0.003},
            "23250": {"ce": 80.0, "ce_delta": 0.50, "ce_theta": -9.0, "ce_iv": 17.0, "ce_gamma": 0.004},
            "23300": {"ce": 55.0, "ce_delta": 0.38, "ce_theta": -10.0, "ce_iv": 18.0, "ce_gamma": 0.004},
        },
    )
    assert pick_paper_strike(tick, "CE", 23250.0, "NIFTY") == 23200.0


def test_filled_close_applies_groww_and_stt() -> None:
    from desk_ml.groww_costs import groww_round_trip_charges, net_pnl_inr
    from desk_ml.paper_scalp import BookEngine, OpenPaper, _close

    engine = BookEngine()
    engine.equity["MIX-DEFAULT-BUY"] = 10000.0
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="fill-cost",
        entry=100.0,
        stop=80.0,
        target=130.0,
        atm_strike=23200.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="TEST",
        limit_price=100.0,
        lot_size=65,
        lots=1,
        qty=65,
        filled=True,
    )
    _close(engine, pos, ltp=110.0, ts=_ts(5), reason="TARGET")
    row = engine.closed[0]
    expect = groww_round_trip_charges(exit_premium=110.0, qty=65, filled=True)
    assert row["gross_pnl_inr"] == 650.0
    assert row["brokerage_inr"] == 40.0
    assert row["charges_inr"] == expect["charges_inr"]
    assert row["realized_pnl_inr"] == net_pnl_inr(gross_inr=650.0, charges_inr=expect["charges_inr"])
    assert row["result"] == "SUCCESS"


def test_unfilled_close_has_zero_charges() -> None:
    from desk_ml.paper_scalp import BookEngine, OpenPaper, _close

    engine = BookEngine()
    engine.equity["MIX-DEFAULT-BUY"] = 10000.0
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="unfill-cost",
        entry=100.0,
        stop=80.0,
        target=130.0,
        atm_strike=23200.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="TEST",
        limit_price=100.0,
        lot_size=65,
        lots=1,
        qty=65,
        filled=False,
    )
    _close(engine, pos, ltp=110.0, ts=_ts(5), reason="CANCEL_UNFILLED_AWAY")
    row = engine.closed[0]
    assert row["result"] == "CANCELLED"
    assert row["charges_inr"] == 0.0
    assert row["realized_pnl_inr"] == 0.0


def _sensex_tick(*, i: int, idx: float, atm: float, wings: dict, ce: float, pe: float) -> Triple:
    itm_ce = atm - 100.0
    cell_itm = wings.get(str(int(itm_ce))) or {}
    cell_atm = wings.get(str(int(atm))) or {}
    return Triple(
        ts=_ts(i),
        idx_close=idx,
        ce_close=float(cell_atm.get("ce") or ce),
        pe_close=pe,
        atm_strike=atm,
        ce_low=float(cell_atm.get("ce_low") or cell_atm.get("ce") or ce),
        itm_ce_close=cell_itm.get("ce"),
        itm_ce_strike=itm_ce,
        itm_ce_low=cell_itm.get("ce_low") or cell_itm.get("ce"),
        wing_quotes=wings,
    )


def test_quote_for_side_does_not_use_rolled_atm_for_74300() -> None:
    tick = _sensex_tick(
        i=10,
        idx=74457.0,
        atm=74500.0,
        ce=165.0,
        pe=170.0,
        wings={
            "74300": {"ce": 269.05, "pe": 120.0, "ce_low": 217.35},
            "74400": {"ce": 209.7, "pe": 140.0},
            "74500": {"ce": 165.0, "pe": 170.0},
        },
    )
    ltp, low, src = quote_for_side(tick, "CE", strike=74300.0)
    assert ltp == 269.05
    assert low == 217.35
    assert src.startswith("STRIKE_74300")
    missing = Triple(
        ts=_ts(11),
        idx_close=74457.0,
        ce_close=165.0,
        pe_close=170.0,
        atm_strike=74500.0,
        itm_ce_close=209.7,
        itm_ce_strike=74400.0,
        wing_quotes={"74500": {"ce": 165.0, "pe": 170.0}},
    )
    ltp2, _, src2 = quote_for_side(missing, "CE", strike=74300.0)
    assert ltp2 is None
    assert src2 == "MISSING_STRIKE"


def test_merge_wing_quotes_keeps_strike_low() -> None:
    merged = merge_wing_quotes(
        {"74300": {"ce": 217.35, "pe": 193.0}},
        {"74300": {"ce": 243.7, "pe": 176.0}, "74500": {"ce": 191.0, "pe": 160.0}},
    )
    assert merged["74300"]["ce"] == 243.7
    assert merged["74300"]["ce_low"] == 217.35
    assert merged["74500"]["ce"] == 191.0


def test_sensex_74300_ce_fill_then_sl_closes_loss() -> None:
    engine = BookEngine()
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="SENSEX",
        side="CE",
        trade_id="paper-sensex-74300-sl",
        entry=234.8,
        stop=199.58,
        target=630.0,
        atm_strike=74300.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="ITM_100",
        limit_price=231.9824,
        filled=False,
        lot_size=20,
        lots=1,
        qty=20,
    )
    engine.opens[("MIX-DEFAULT-BUY", "SENSEX")] = pos
    fill = _sensex_tick(
        i=1,
        idx=74352.0,
        atm=74300.0,
        ce=217.35,
        pe=193.65,
        wings={"74300": {"ce": 217.35, "pe": 193.65}, "74200": {"ce": 276.4, "pe": 150.0}},
    )
    mark_to_market(engine, fill, "SENSEX", 2, atm_strike=74300.0)
    assert engine.opens[("MIX-DEFAULT-BUY", "SENSEX")].filled is True
    assert engine.opens[("MIX-DEFAULT-BUY", "SENSEX")].entry == 217.35
    dump = _sensex_tick(
        i=2,
        idx=74402.0,
        atm=74400.0,
        ce=191.0,
        pe=176.0,
        wings={
            "74300": {"ce": 180.0, "pe": 176.2, "ce_low": 180.0},
            "74400": {"ce": 191.0, "pe": 160.0},
            "74200": {"ce": 243.7, "pe": 140.0},
        },
    )
    mark_to_market(engine, dump, "SENSEX", 3, atm_strike=74400.0)
    assert ("MIX-DEFAULT-BUY", "SENSEX") not in engine.opens
    row = engine.closed[-1]
    assert row["exit_reason"] == "STOP"
    assert row["result"] == "LOSS"
    assert row["filled"] is True
    assert row["sl_hit"] is True


def test_sensex_74300_ce_same_tick_limit_and_stop_closes() -> None:
    engine = BookEngine()
    pos = OpenPaper(
        book_id="MIX-ML-LOGIT",
        underlying="SENSEX",
        side="CE",
        trade_id="paper-sensex-74300-gap",
        entry=234.8,
        stop=199.58,
        target=630.0,
        atm_strike=74300.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="ITM_100",
        limit_price=231.9824,
        filled=False,
        lot_size=20,
        lots=1,
        qty=20,
    )
    engine.opens[("MIX-ML-LOGIT", "SENSEX")] = pos
    gap = _sensex_tick(
        i=1,
        idx=74320.0,
        atm=74300.0,
        ce=180.0,
        pe=210.0,
        wings={"74300": {"ce": 180.0, "pe": 210.0, "ce_low": 175.0}},
    )
    mark_to_market(engine, gap, "SENSEX", 2, atm_strike=74300.0)
    assert ("MIX-ML-LOGIT", "SENSEX") not in engine.opens
    row = engine.closed[-1]
    assert row["exit_reason"] == "STOP"
    assert row["result"] == "LOSS"
    assert row["filled"] is True


def test_sensex_74300_stays_open_when_only_rolled_atm_dumps() -> None:
    engine = BookEngine()
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="SENSEX",
        side="CE",
        trade_id="paper-sensex-74300-itm",
        entry=217.35,
        stop=199.58,
        target=630.0,
        atm_strike=74300.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="ITM_100",
        limit_price=231.9824,
        filled=True,
        lot_size=20,
        lots=1,
        qty=20,
    )
    engine.opens[("MIX-DEFAULT-BUY", "SENSEX")] = pos
    rolled = _sensex_tick(
        i=3,
        idx=74457.0,
        atm=74500.0,
        ce=165.0,
        pe=170.0,
        wings={
            "74300": {"ce": 269.05, "pe": 120.0},
            "74400": {"ce": 209.7, "pe": 140.0},
            "74500": {"ce": 165.0, "pe": 170.0},
        },
    )
    mark_to_market(engine, rolled, "SENSEX", 4, atm_strike=74500.0)
    still = engine.opens[("MIX-DEFAULT-BUY", "SENSEX")]
    assert still.filled is True
    assert still.last_ltp == 269.05
    assert not engine.closed


def test_sideways_does_not_skip_stop_on_open_ticket() -> None:
    engine = BookEngine(skip_new_when_sideways=True)
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="SENSEX",
        side="CE",
        trade_id="paper-sensex-sideways-sl",
        entry=217.35,
        stop=199.58,
        target=630.0,
        atm_strike=74300.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="ITM_100",
        limit_price=231.9824,
        filled=True,
        index_regime="SIDEWAYS",
    )
    engine.opens[("MIX-DEFAULT-BUY", "SENSEX")] = pos
    dump = _sensex_tick(
        i=5,
        idx=74300.0,
        atm=74300.0,
        ce=180.0,
        pe=200.0,
        wings={"74300": {"ce": 180.0, "pe": 200.0}},
    )
    mark_to_market(engine, dump, "SENSEX", 6, dealer_verdict="HOLD", atm_strike=74300.0)
    assert engine.closed[-1]["exit_reason"] == "STOP"


