"""Parallel paper scalpers: independent books, feasible scalp exits, paper hit rate."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from desk_ml.features import Triple
from desk_ml.paper_scalp import (
    BookEngine,
    CANCEL_BIN_ROLL,
    LIVE_BOOKS,
    OpenPaper,
    REGIME_UNKNOWN_WAIT,
    SIDEWAYS_HOLD,
    TRAIL_BAND_MAX,
    TRAIL_BAND_MIN,
    cancel_if_bin_rolled,
    classify_index_regime,
    feasibility_long,
    itm_bins_picture,
    logit_side_series,
    mark_to_market,
    paper_hit_rate,
    propose_levels,
    quote_for_side,
    render_markdown,
    replay_paper_scalp,
    save_human_override,
    score_itm_bin,
    seen_not_taken_picture,
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
        atm = round(idx / 50.0) * 50.0
        ce_itm, pe_itm = atm - 200.0, atm + 200.0
        ce_bn, pe_bn = atm - 300.0, atm + 300.0
        out.append(
            Triple(
                ts=_ts(i),
                idx_close=idx,
                ce_close=ce,
                pe_close=pe,
                atm_strike=atm,
                itm_ce_close=ce + 40.0,
                itm_pe_close=pe + 40.0,
                itm_ce_strike=ce_itm,
                itm_pe_strike=pe_itm,
                idx_volume=80.0 + i * 6.0,
                wing_quotes={
                    str(int(ce_bn)): {"ce": ce + 55.0, "pe": 15.0},
                    str(int(ce_itm)): {"ce": ce + 40.0, "pe": 20.0},
                    str(int(atm)): {"ce": ce, "pe": pe},
                    str(int(pe_itm)): {"ce": 20.0, "pe": pe + 40.0},
                    str(int(pe_bn)): {"ce": 15.0, "pe": pe + 55.0},
                },
            )
        )
    return out


def _chop_triples(*, n: int = 80) -> list[Triple]:
    out: list[Triple] = []
    idx, ce, pe = 25000.0, 120.0, 110.0
    for i in range(n):
        idx += 4.0 if i % 2 == 0 else -4.0
        ce = max(8.0, 120.0 + (2.0 if i % 2 == 0 else -2.0))
        pe = max(8.0, 110.0 + (-2.0 if i % 2 == 0 else 2.0))
        out.append(
            Triple(
                ts=_ts(i),
                idx_close=idx,
                ce_close=ce,
                pe_close=pe,
                atm_strike=25000.0,
                itm_ce_close=ce + 40.0,
                itm_pe_close=pe + 40.0,
                itm_ce_strike=24800.0,
                itm_pe_strike=25200.0,
                wing_quotes={
                    "24800": {"ce": ce + 40.0, "pe": 20.0},
                    "25000": {"ce": ce, "pe": pe},
                    "25200": {"ce": 20.0, "pe": pe + 40.0},
                },
            )
        )
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


def test_open_settle_skips_new_opens_flatten_still_ok() -> None:
    from desk_ml.paper_scalp import OpenPaper, mark_to_market

    morning = []
    idx, ce, pe = 25000.0, 120.0, 110.0
    base = datetime(2026, 9, 17, 9, 0, tzinfo=IST)
    for i in range(40):
        idx += 8.0
        ce += 1.2
        morning.append(
            Triple(
                ts=int(base.timestamp()) + i * 60,
                idx_close=idx,
                ce_close=ce,
                pe_close=pe,
            )
        )
    engine = BookEngine()
    step_underlying(
        engine,
        underlying="NIFTY",
        triples=morning,
        i=20,
        ml001_hold=False,
        ml002_hold=False,
        follow_gap=False,
        logit={"side": "CE", "status": "OK"},
        logit_xr={"side": "CE", "status": "OK"},
        ml1={"status": "OK", "take": True},
        tv_side="CE",
        deny_model_signals=False,
    )
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert any(s.get("reason") in {"NO_NEW_BEFORE_0930", "OPEN_SETTLE_35M", "NO_NEW_BEFORE_0950"} for s in engine.skips)
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="already-open-settle",
        entry=120.0,
        stop=80.0,
        target=140.0,
        atm_strike=24800.0,
        opened_ts=int(datetime(2026, 9, 17, 9, 10, tzinfo=IST).timestamp()),
        opened_bar=10,
        strike_source="ITM_100",
        limit_price=120.0,
        filled=True,
        index_regime="TREND",
    )
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos
    engine.equity["MIX-DEFAULT-BUY"] = 10000.0
    tick = Triple(
        ts=int(datetime(2026, 9, 17, 9, 21, tzinfo=IST).timestamp()),
        idx_close=25000.0,
        ce_close=70.0,
        pe_close=110.0,
        atm_strike=25000.0,
        itm_ce_close=70.0,
        itm_ce_strike=24800.0,
    )
    mark_to_market(engine, tick, "NIFTY", 31)
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False


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
        opened_ts=int(__import__("datetime").datetime(2026, 9, 10, 15, 14, tzinfo=IST).timestamp()),
        opened_bar=49,
        strike_source="TEST",
        limit_price=120.0,
        filled=True,
        index_regime="TREND",
    )
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos
    engine.equity["MIX-DEFAULT-BUY"] = 10000.0
    late = int(__import__("datetime").datetime(2026, 9, 10, 15, 16, tzinfo=IST).timestamp())
    tick = Triple(ts=late, idx_close=25000.0, ce_close=118.0, pe_close=110.0)
    mark_to_market(engine, tick, "NIFTY", 50)
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert engine.closed and engine.closed[0]["exit_reason"] in {"FLATTEN_1516", "FLATTEN_1515"}


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


def test_open_settle_blocks_new_before_0930() -> None:
    from desk_ml.paper_scalp import new_paper_blocked

    early = int(datetime(2026, 9, 17, 9, 15, tzinfo=IST).timestamp())
    almost = int(datetime(2026, 9, 17, 9, 29, tzinfo=IST).timestamp())
    open_ok = int(datetime(2026, 9, 17, 9, 30, tzinfo=IST).timestamp())
    sat = int(datetime(2026, 9, 19, 12, 0, tzinfo=IST).timestamp())
    assert new_paper_blocked(early) == "NO_NEW_BEFORE_0930"
    assert new_paper_blocked(almost) == "NO_NEW_BEFORE_0930"
    assert new_paper_blocked(open_ok) is None
    assert new_paper_blocked(sat) == "WEEKEND_NO_MARKET"


def test_fantasy_266_219_615_clipped_or_fail() -> None:
    dec = evaluate_long_premium(
        entry=266.0,
        stop=219.0,
        target=615.0,
        typical_premium_range=634.0,
    )
    assert dec.ok is False
    assert dec.reason_code == "TARGET_FEASIBILITY_FAIL"
    contaminated = [50.0, 80.0, 266.0, 684.0, 74300.0]
    levels = propose_levels(266.0, contaminated)
    assert levels["target"] < 400.0
    assert levels["target"] < 615.0
    # unsanitized 0.55*(684-50)+266 ≈ 615; sanitizer or R-cap must prevent that print
    rr = (levels["target"] - levels["entry"]) / max(1e-9, levels["entry"] - levels["stop"])
    assert rr <= 2.0 + 1e-6


def test_iv_widens_stop_not_target() -> None:
    from desk_ml.paper_scalp import greeks_paper_adjust

    base = greeks_paper_adjust(entry=266.0, stop_frac=0.40, target_frac=0.55)
    iv = greeks_paper_adjust(entry=266.0, stop_frac=0.40, target_frac=0.55, iv=30.0)
    assert iv["target_frac"] <= base["target_frac"]
    assert iv["stop_frac"] >= base["stop_frac"]


def test_recent_closed_newest_first() -> None:
    from desk_ml.paper_scalp import recent_closed_first

    rows = [
        {"trade_id": "old", "closed_ts": 100},
        {"trade_id": "new", "closed_ts": 200},
    ]
    out = recent_closed_first(rows)
    assert out[0]["trade_id"] == "new"


def test_order_tickets_open_then_closed_last_updated() -> None:
    from desk_ml.paper_scalp import order_tickets_last_updated

    closed = [
        {"trade_id": "c-old", "closed_ts": 100, "last_updated_ts": 100},
        {"trade_id": "c-new", "closed_ts": 300, "last_updated_ts": 300},
    ]
    open_rows = [
        {"trade_id": "o-old", "opened_ts": 50, "last_updated_ts": 150},
        {"trade_id": "o-new", "opened_ts": 80, "last_updated_ts": 400},
    ]
    o = order_tickets_last_updated(open_rows)
    c = order_tickets_last_updated(closed)
    tickets = o + c
    assert [t["trade_id"] for t in tickets] == ["o-new", "o-old", "c-new", "c-old"]


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
    from desk_ml.paper_scalp import DESK_CAPITAL_INR, allocate_desk_capital, LIVE_BOOKS

    plan = allocate_desk_capital(tradable=[b for b in LIVE_BOOKS if b != "MIX-ML-GREEKS"])
    assert plan["desk_capital_inr"] == DESK_CAPITAL_INR
    assert plan["per_book"]["MIX-ML-GREEKS"] == 0.0
    active = [b for b in LIVE_BOOKS if b != "MIX-ML-GREEKS"]
    assert sum(plan["per_book"][b] for b in active) == DESK_CAPITAL_INR


def test_allocate_fill_books_not_eight_clones() -> None:
    from desk_ml.paper_scalp import DESK_CAPITAL_INR, allocate_desk_capital, tradable_fill_books

    plan = allocate_desk_capital(tradable=tradable_fill_books(has_greeks=False))
    assert plan["tradable"] == ["MIX-DEFAULT-BUY"]
    assert plan["n_tradable"] == 1
    assert plan["per_book"]["MIX-DEFAULT-BUY"] == DESK_CAPITAL_INR
    assert plan["per_book"]["ML-001"] == 0.0
    assert plan["per_book"]["MIX-ML-LOGIT"] == 0.0
    assert sum(plan["per_book"][b] for b in plan["tradable"]) == DESK_CAPITAL_INR


def test_allocate_old_engine_splits_lab_when_sod_off() -> None:
    from desk_ml.paper_scalp import DESK_CAPITAL_INR, allocate_desk_capital, tradable_fill_books

    plan = allocate_desk_capital(tradable=tradable_fill_books(has_greeks=False, sod_one_ticket=False))
    assert plan["skipped"] == ["ML-001", "ML-002", "ML-1", "MIX-TV-EP-024", "MIX-ML-GREEKS"]
    assert plan["tradable"] == ["MIX-DEFAULT-BUY", "MIX-ML-LOGIT", "MIX-ML-LOGIT-XR"]
    assert plan["n_tradable"] == 3
    assert plan["per_book"]["ML-001"] == 0.0
    assert sum(plan["per_book"][b] for b in plan["tradable"]) == DESK_CAPITAL_INR


def test_size_lots_twenty_five_on_desk_capital() -> None:
    from desk_ml.paper_lots import size_lots
    from desk_ml.paper_scalp import DESK_CAPITAL_INR

    row = size_lots(entry=150.0, lot_size=65, capital_inr=DESK_CAPITAL_INR)
    assert row["lots"] == 25
    assert row["qty"] == 1625
    assert row["lot_status"] == "OK"
    cheap = size_lots(entry=80.0, lot_size=65, capital_inr=DESK_CAPITAL_INR)
    assert cheap["lots"] == 25
    skip = size_lots(entry=400.0, lot_size=65, capital_inr=50000.0)
    assert skip["lots"] == 0
    assert skip["lot_status"] == "SKIP_BELOW_MIN_LOTS"


def test_resolve_fill_intents_hold_skip_logit_fill_dealer_not_against() -> None:
    from desk_ml.paper_scalp import resolve_fill_intents

    out = resolve_fill_intents(
        dealer_confirm=None,
        dealer_verdict="HOLD",
        logit={"side": "CE", "status": "OK"},
        logit_xr={"side": None, "status": "SKIP", "reason": "no xr"},
        ml001_hold=True,
        follow_gap=True,
        ml002_hold=False,
        ml1={"status": "OK", "take": True},
    )
    assert out["ML-001"] == (None, "ML-001_HOLD")
    assert out["MIX-ML-LOGIT"] == ("CE", None)
    assert out["MIX-DEFAULT-BUY"][0] is None
    assert "VS_LOGIT_CE" in str(out["MIX-DEFAULT-BUY"][1])
    assert out["MIX-TV-EP-024"] == (None, "OBSERVE_NO_OWN_FILL")
    assert out["MIX-ML-LOGIT-XR"][0] is None
    assert out["MIX-ML-GREEKS"] == (None, "GREEKS_NO_CLONE")


def test_resolve_fill_dealer_confirms_matching_logit() -> None:
    from desk_ml.paper_scalp import resolve_fill_intents

    out = resolve_fill_intents(
        dealer_confirm="CE",
        dealer_verdict="BUY_CE_CONFIRM",
        logit={"side": "CE", "status": "OK"},
        logit_xr={"side": "CE", "status": "OK"},
        ml001_hold=False,
        follow_gap=False,
        ml002_hold=False,
        ml1={"status": "OK", "take": True},
    )
    assert out["MIX-DEFAULT-BUY"] == ("CE", None)
    assert out["MIX-ML-LOGIT-XR"] == ("CE", None)


def test_trend_up_kills_new_pe_not_a_strat() -> None:
    triples = _triples(n=50, trend=8.0)
    engine = BookEngine(sod_one_ticket=False, picker_majority=False)
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
    pe_open = engine.opens.get(("MIX-ML-LOGIT", "NIFTY"))
    assert pe_open is None or pe_open.side != "PE"
    assert any(
        str(s.get("reason") or "") == "TREND_UP_KILL_PE"
        for s in engine.skips
        if s.get("underlying") == "NIFTY"
    )


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
    engine = BookEngine(sod_one_ticket=False, picker_majority=False)
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
    ml001_open = engine.has_open("ML-001", "NIFTY")
    tv_open = engine.has_open("MIX-TV-EP-024", "NIFTY")
    assert ml001_open is False
    assert tv_open is False
    assert any(s.get("book_id") == "ML-001" and s.get("reason") == "ML-001_HOLD" for s in engine.skips)
    skip_books = {s["book_id"] for s in engine.skips if s["book_id"] in {"ML-001", "ML-002"}}
    assert "ML-001" in skip_books


def test_logit_fills_dealer_does_not_clone_observe_books() -> None:
    triples = _triples()
    engine = BookEngine(sod_one_ticket=False, picker_majority=False)
    step_underlying(
        engine,
        underlying="NIFTY",
        triples=triples,
        i=40,
        ml001_hold=True,
        ml002_hold=True,
        follow_gap=True,
        logit={"side": "CE", "status": "OK"},
        logit_xr={"side": None, "status": "SKIP"},
        ml1={"status": "DATA_INSUFFICIENT", "reason": "no labels"},
        tv_side="CE",
        deny_model_signals=True,
    )
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is True
    assert engine.opens[("MIX-ML-LOGIT", "NIFTY")].side == "CE"
    assert engine.has_open("ML-001", "NIFTY") is False
    assert engine.has_open("ML-002", "NIFTY") is False
    assert engine.has_open("ML-1", "NIFTY") is False
    assert engine.has_open("MIX-TV-EP-024", "NIFTY") is False
    dealer = engine.has_open("MIX-DEFAULT-BUY", "NIFTY")
    if dealer:
        assert engine.opens[("MIX-DEFAULT-BUY", "NIFTY")].side == "CE"
    else:
        assert any(
            s.get("book_id") == "MIX-DEFAULT-BUY" and "VS_LOGIT_CE" in str(s.get("reason") or "")
            for s in engine.skips
        )


def test_one_open_per_book_underlying() -> None:
    triples = _triples()
    engine = BookEngine(sod_one_ticket=False, picker_majority=False)
    for i in (30, 31, 32):
        step_underlying(
            engine,
            underlying="NIFTY",
            triples=triples,
            i=i,
            ml001_hold=False,
            ml002_hold=False,
            follow_gap=False,
            logit={"side": "CE", "status": "OK"},
            logit_xr={"side": None, "status": "SKIP"},
            ml1={"status": "DATA_INSUFFICIENT", "reason": "no labels"},
            tv_side="CE",
        )
    assert sum(1 for (b, u) in engine.opens if b == "MIX-ML-LOGIT" and u == "NIFTY") <= 1
    assert engine.has_open("MIX-TV-EP-024", "NIFTY") is False
    assert engine.has_open("ML-001", "NIFTY") is False


def test_scalp_time_exit_closes_premium_pnl() -> None:
    triples = _triples(n=80)
    engine = BookEngine(sod_one_ticket=False, picker_majority=False)
    for i in range(20, 70):
        step_underlying(
            engine,
            underlying="NIFTY",
            triples=triples,
            i=i,
            ml001_hold=True,
            ml002_hold=True,
            follow_gap=True,
            logit={"side": "CE", "status": "OK"},
            logit_xr={"side": None, "status": "SKIP"},
            ml1={"status": "DATA_INSUFFICIENT", "reason": "no labels"},
            tv_side="CE",
        )
    closed_logit = [c for c in engine.closed if c["book_id"] == "MIX-ML-LOGIT"]
    assert closed_logit
    reasons = {c["exit_reason"] for c in closed_logit}
    assert reasons & {
        "TIME",
        "STOP",
        "TARGET",
        "FLATTEN_1515",
        "FLATTEN_1500",
        "CANCEL_STRIKE_ROLL",
        "CANCEL_ADVERSE",
        "CANCEL_THESIS",
        "CANCEL_UNFILLED_AWAY",
        "CANCEL_UNFILLED_TIMEOUT",
        "CANCEL_UNFILLED_INDEX",
        "CANCEL_UNFILLED_THESIS",
        "CANCEL_UNFILLED_FLAT",
        CANCEL_BIN_ROLL,
        "ITM_ONLY_NO_QUOTE",
        "ITM_ONLY_NOT_ITM",
    }
    assert all(c["realized_pnl"] is not None for c in closed_logit)
    assert all("won" in c for c in closed_logit)
    assert all(c.get("atm_strike") is not None for c in closed_logit)
    assert all("stop" in c and "target" in c for c in closed_logit)


def test_replay_parallel_books_no_promote(tmp_path) -> None:
    from desk_ml.paper_scalp import DESK_CAPITAL_INR, LIVE_BOOKS, replay_paper_scalp

    triples = _triples(n=90)
    board = replay_paper_scalp(
        root=tmp_path,
        underlyings=("NIFTY",),
        triples_by_und={"NIFTY": triples},
        write=False,
    )
    assert board["ok"] is True
    assert board["promote"] is False
    assert board["independent_books"] is False
    assert board["sod_one_ticket"] is True
    ids = {m["model_id"] for m in board["models"]}
    assert ids == set(LIVE_BOOKS)
    assert board["research_ready_for_programming"] is False
    assert board["execution"] == "refused"
    assert board["starting_desk_inr"] == DESK_CAPITAL_INR
    assert board["capital_plan"]["tradable"] == ["MIX-DEFAULT-BUY"]
    assert "MIX-ML-LOGIT" in board["capital_plan"]["skipped"]
    assert board["deny_model_signals"] is True
    assert board["win_rate_kind"] == "paper_closed_net_inr_gt_0_after_groww_stt"
    assert "win_rate_gross_pct" in board
    assert "book_rank" in board
    assert "today" in board
    assert board["cost_model"]["name"] == "GROWW_FO_20_PLUS_STATUTORY_OPTIONS"
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
    engine = BookEngine(skip_bn_unless_last3=False, skip_banknifty=False, sod_one_ticket=False, picker_majority=False)
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
        assert t.get("result") in {"SUCCESS", "LOSS", "CANCELLED", "TIME", "FLATTEN"}
        assert t.get("status") in {"CLOSED_PAPER", "CLOSED_CANCEL", "CANCELLED", "CANCELLED_UNFILLED"}
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

    assert itm_wing_strikes("NIFTY", 23500.0) == {"CE": 23300.0, "PE": 23700.0}
    assert itm_wing_strikes("SENSEX", 74300.0) == {"CE": 74000.0, "PE": 74600.0}
    assert itm_wing_strikes("NIFTY", 23250.0) == {"CE": 23050.0, "PE": 23450.0}
    from desk_ml.paper_scalp import is_buy_itm, is_deep_itm, paper_itm_strike

    tick = Triple(
        ts=_ts(0),
        idx_close=74374.0,
        ce_close=180.0,
        pe_close=190.0,
        atm_strike=74300.0,
    )
    assert paper_itm_strike(tick, "CE", "SENSEX") == 74000.0
    assert is_buy_itm("CE", 74300.0, tick, "SENSEX") is False
    assert is_buy_itm("CE", 74200.0, tick, "SENSEX") is True
    assert is_deep_itm("CE", 74200.0, tick, "SENSEX") is False
    assert is_deep_itm("CE", 74000.0, tick, "SENSEX") is True


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
        itm_ce_strike=74000.0,
        itm_pe_strike=74600.0,
        wing_quotes={
            "74000": {"ce": 450.0, "pe": 90.0},
            "74300": {"ce": 300.0, "pe": 305.0},
            "74600": {"ce": 90.0, "pe": 440.0},
        },
    )
    engine = BookEngine(skip_bn_unless_last3=False, sensex_need_strength=False)
    engine.last_regime["SENSEX"] = {"regime": "TREND", "direction": "UP"}
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
    assert pos.atm_strike == 74000.0
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


def test_no_new_paper_after_1515_ist() -> None:
    from desk_ml.paper_scalp import BookEngine, _try_open, new_paper_blocked

    still_ok = int(datetime(2026, 9, 10, 15, 15, tzinfo=IST).timestamp())
    assert new_paper_blocked(still_ok) is None
    late = int(datetime(2026, 9, 10, 15, 16, tzinfo=IST).timestamp())
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
    assert any(s.get("reason") in {"NO_NEW_AFTER_1516", "NO_NEW_AFTER_1515"} for s in engine.skips)


def test_greeks_adjust_delta_skip_and_iv_widens_stop() -> None:
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
            "23000": {"ce": 190.0, "ce_delta": 0.56, "ce_theta": -6.0, "ce_iv": 15.5, "ce_gamma": 0.001},
            "23050": {"ce": 170.0, "ce_delta": 0.70, "ce_theta": -6.5, "ce_iv": 15.8, "ce_gamma": 0.001},
            "23150": {"ce": 140.0, "ce_delta": 0.62, "ce_theta": -7.0, "ce_iv": 16.0, "ce_gamma": 0.002},
            "23200": {"ce": 110.0, "ce_delta": 0.56, "ce_theta": -8.0, "ce_iv": 16.5, "ce_gamma": 0.003},
            "23250": {"ce": 80.0, "ce_delta": 0.50, "ce_theta": -9.0, "ce_iv": 17.0, "ce_gamma": 0.004},
            "23300": {"ce": 55.0, "ce_delta": 0.38, "ce_theta": -10.0, "ce_iv": 18.0, "ce_gamma": 0.004},
        },
    )
    assert pick_paper_strike(tick, "CE", 23250.0, "NIFTY") == 23000.0


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
    expect = groww_round_trip_charges(exit_premium=110.0, entry_premium=100.0, qty=65, filled=True)
    assert row["gross_pnl_inr"] == 650.0
    assert row["brokerage_inr"] == 40.0
    assert row["charges_inr"] == expect["charges_inr"]
    assert row["realized_pnl_inr"] == net_pnl_inr(gross_inr=650.0, charges_inr=expect["charges_inr"])
    assert row["result"] == "SUCCESS"


def test_paper_justification_survives_success_and_cancel() -> None:
    from desk_ml.paper_scalp import (
        BookEngine,
        OpenPaper,
        _close,
        paper_close_justification,
        paper_open_justification,
        render_markdown,
    )

    engine = BookEngine(nifty_allow_sides=("PE",), nifty_need_strength=True, nifty_max_filled_per_book=4)
    why = paper_open_justification(
        underlying="NIFTY",
        side="PE",
        classified={
            "regime": "TREND",
            "direction": "DOWN",
            "itm_bin": {"side": "PE"},
            "last3_impulse": "DOWN",
        },
        levels={"stop": 90.0, "target": 140.0},
        strike=23400.0,
        strike_source="ITM_100",
        engine=engine,
    )
    assert "overlay=PE+strength+max4" in why
    assert "PAPER only" in why
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="PE",
        trade_id="just-ok",
        entry=100.0,
        stop=90.0,
        target=140.0,
        atm_strike=23400.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="ITM_100",
        limit_price=100.0,
        lot_size=65,
        lots=1,
        qty=65,
        filled=True,
        justification=why,
    )
    _close(engine, pos, ltp=130.0, ts=_ts(5), reason="TARGET")
    row = engine.closed[0]
    assert row["result"] == "SUCCESS"
    assert "CLOSE:" in row["justification"]
    assert "EXIT TARGET" in row["justification"]
    assert "result=SUCCESS" in row["justification"]
    md = render_markdown({"open_trades": [], "closed_trades": [row], "title": "t"})
    assert "Closed justification" in md
    assert "EXIT TARGET" in md
    md_open = render_markdown(
        {
            "open_trades": [
                {
                    "book_id": "MIX-DEFAULT-BUY",
                    "underlying": "NIFTY",
                    "side": "CE",
                    "atm_strike": 23250.0,
                    "limit_price": 170.0,
                    "target": 195.5,
                    "stop": 158.0,
                    "last_ltp": 172.0,
                    "filled": True,
                    "status": "OPEN_PAPER",
                    "index_regime": "TREND",
                    "last_updated_ist": "2026-09-18T12:00:00+05:30",
                }
            ],
            "closed_trades": [],
            "title": "t",
        }
    )
    assert "**target**" in md_open
    assert "195.5" in md_open
    close_txt = paper_close_justification(
        open_why=why,
        reason="CANCEL_UNFILLED_AWAY",
        result="CANCELLED",
        status="CANCELLED_UNFILLED",
        unfilled=True,
        inr=0.0,
        sl_hit=False,
    )
    assert "result=CANCELLED" in close_txt
    assert "₹0 unfilled" in close_txt


def test_time_green_is_not_success() -> None:
    from desk_ml.paper_scalp import BookEngine, OpenPaper, _close, paper_close_result, render_markdown

    assert paper_close_result(unfilled=False, reason="TIME", won=True) == "TIME"
    assert paper_close_result(unfilled=False, reason="TARGET", won=True) == "SUCCESS"
    engine = BookEngine()
    engine.equity["MIX-DEFAULT-BUY"] = 17500.0
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="PE",
        trade_id="pe-time-not-tgt",
        entry=131.9,
        stop=121.4523,
        target=148.8023,
        atm_strike=23400.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="ITM_100",
        limit_price=131.9,
        lot_size=65,
        lots=2,
        qty=130,
        filled=True,
    )
    _close(engine, pos, ltp=139.65, ts=_ts(9), reason="TIME")
    row = engine.closed[0]
    assert row["exit"] == 139.65
    assert row["target"] == 148.8023
    assert row["exit"] < row["target"]
    assert row["won"] is True
    assert row["target_hit"] is False
    assert row["result"] == "TIME"
    assert row["exit_reason"] == "TIME"
    assert "target_hit=false" in row["justification"]
    md = render_markdown({"open_trades": [], "closed_trades": [row], "title": "t", "today": {}})
    assert "`TIME`" in md
    assert "139.65" in md
    from desk_ml.paper_scalp import coerce_close_result

    old = {"exit_reason": "TIME", "result": "SUCCESS", "target_hit": None}
    assert coerce_close_result(old)["result"] == "TIME"
    assert coerce_close_result(old)["target_hit"] is False


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
    assert row["status"] == "CANCELLED_UNFILLED"
    assert row["charges_inr"] == 0.0
    assert row["brokerage_inr"] == 0.0
    assert row["gst_inr"] == 0.0
    assert row["stt_inr"] == 0.0
    assert row["realized_pnl_inr"] == 0.0
    assert row["gross_pnl_inr"] == 0.0


def test_filled_cancel_still_books_round_trip_pnl() -> None:
    """CANCEL_BIN_ROLL after a fill is a paper round-trip, not ₹0. Status CLOSED_CANCEL."""
    from desk_ml.groww_costs import groww_round_trip_charges, net_pnl_inr
    from desk_ml.paper_scalp import BookEngine, OpenPaper, _close

    engine = BookEngine()
    engine.equity["MIX-DEFAULT-BUY"] = 10000.0
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="filled-cancel",
        entry=142.1,
        stop=130.0,
        target=157.8,
        atm_strike=23200.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="ITM_100",
        limit_price=142.1,
        lot_size=65,
        lots=1,
        qty=65,
        filled=True,
    )
    _close(engine, pos, ltp=140.2, ts=_ts(5), reason="CANCEL_BIN_ROLL")
    row = engine.closed[0]
    assert row["status"] == "CLOSED_CANCEL"
    assert row["filled"] is True
    assert row["result"] == "LOSS"
    assert row["sl_hit"] is False
    assert row["sl_loss_inr"] is None
    expect = groww_round_trip_charges(exit_premium=140.2, entry_premium=142.1, qty=65, filled=True)
    assert row["charges_inr"] == expect["charges_inr"]
    assert row["realized_pnl_inr"] == net_pnl_inr(
        gross_inr=row["gross_pnl_inr"], charges_inr=expect["charges_inr"]
    )
    assert row["realized_pnl_inr"] < 0



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
        atm_strike=74200.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="ITM_100",
        limit_price=231.9824,
        filled=True,
        last_ltp=276.4,
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
    dump = _sensex_tick(
        i=2,
        idx=74402.0,
        atm=74400.0,
        ce=191.0,
        pe=176.0,
        wings={
            "74300": {"ce": 180.0, "pe": 176.2, "ce_low": 180.0},
            "74400": {"ce": 191.0, "pe": 160.0},
            "74200": {"ce": 190.0, "pe": 140.0, "ce_low": 190.0},
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
        atm_strike=74200.0,
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
        wings={"74300": {"ce": 180.0, "pe": 210.0, "ce_low": 175.0}, "74200": {"ce": 180.0, "pe": 150.0, "ce_low": 175.0}},
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
        atm_strike=74200.0,
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
        wings={"74300": {"ce": 180.0, "pe": 200.0}, "74200": {"ce": 180.0, "pe": 150.0, "ce_low": 180.0}},
    )
    mark_to_market(engine, dump, "SENSEX", 6, dealer_verdict="HOLD", atm_strike=74300.0)
    assert engine.closed[-1]["exit_reason"] == "STOP"


def _ten_sec_trend(*, n: int, trend: float = 8.0) -> list[Triple]:
    out: list[Triple] = []
    idx, ce, pe = 25000.0, 120.0, 110.0
    base = int(datetime(2026, 9, 10, 10, 0, tzinfo=IST).timestamp())
    for i in range(n):
        idx += trend
        ce = max(8.0, ce + trend * 0.15)
        pe = max(8.0, pe - trend * 0.12)
        out.append(Triple(ts=base + i * 10, idx_close=idx, ce_close=ce, pe_close=pe))
    return out


def test_skip_new_open_when_1m_regime_unknown_on_10s_ticks() -> None:
    triples = _ten_sec_trend(n=12)
    engine = BookEngine()
    step_underlying(
        engine,
        underlying="NIFTY",
        triples=triples,
        i=11,
        ml001_hold=False,
        ml002_hold=False,
        follow_gap=False,
        logit={"side": "CE", "status": "OK"},
        logit_xr={"side": "CE", "status": "OK"},
        ml1={"status": "OK", "take": True},
        tv_side="CE",
        deny_model_signals=False,
    )
    assert engine.last_regime["NIFTY"]["n"] < 12
    assert engine.last_regime["NIFTY"]["regime"] == "UNKNOWN"
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is False
    assert any(
        s.get("reason") == REGIME_UNKNOWN_WAIT and s.get("book_id") == "MIX-DEFAULT-BUY"
        for s in engine.skips
    )


def test_allow_new_open_after_12_1m_trend_bars() -> None:
    triples = _triples(n=20, trend=8.0)
    engine = BookEngine()
    step_underlying(
        engine,
        underlying="NIFTY",
        triples=triples,
        i=12,
        ml001_hold=False,
        ml002_hold=False,
        follow_gap=False,
        logit={"side": "CE", "status": "OK"},
        logit_xr={"side": "CE", "status": "OK"},
        ml1={"status": "OK", "take": True},
        tv_side="CE",
        deny_model_signals=False,
    )
    assert engine.last_regime["NIFTY"]["n"] >= 12
    assert engine.last_regime["NIFTY"]["regime"] == "TREND"
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is True or engine.has_open(
        "MIX-ML-LOGIT", "NIFTY"
    )


def test_unknown_1m_still_marks_open_ticket_every_10s() -> None:
    triples = _ten_sec_trend(n=8)
    engine = BookEngine()
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="already-open-unknown",
        entry=120.0,
        stop=80.0,
        target=140.0,
        atm_strike=24800.0,
        opened_ts=triples[0].ts,
        opened_bar=0,
        strike_source="ITM_100",
        limit_price=120.0,
        filled=True,
        index_regime="TREND",
    )
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos
    engine.equity["MIX-DEFAULT-BUY"] = 10000.0
    dump = Triple(
        ts=triples[-1].ts,
        idx_close=triples[-1].idx_close,
        ce_close=70.0,
        pe_close=110.0,
        atm_strike=25000.0,
        itm_ce_close=70.0,
        itm_ce_strike=24800.0,
    )
    mark_to_market(engine, dump, "NIFTY", 7)
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert engine.closed[-1]["exit_reason"] == "STOP"


def test_unfilled_timeout_is_120s_not_two_10s_bars() -> None:
    from desk_ml.paper_scalp import OpenPaper, _unfilled_reason

    opened = int(datetime(2026, 9, 10, 10, 0, tzinfo=IST).timestamp())
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="wait-10s",
        entry=100.0,
        stop=80.0,
        target=130.0,
        atm_strike=23200.0,
        opened_ts=opened,
        opened_bar=0,
        strike_source="TEST",
        limit_price=100.0,
        filled=False,
    )
    assert _unfilled_reason(pos, 101.0, opened + 20, 2) is None
    assert _unfilled_reason(pos, 101.0, opened + 119, 20) is None
    assert _unfilled_reason(pos, 101.0, opened + 120, 20) == "CANCEL_UNFILLED_TIMEOUT"


def test_time_exit_is_wall_clock_not_10s_bar_i() -> None:
    from desk_ml.paper_scalp import OpenPaper, _exit_reason

    opened = int(datetime(2026, 9, 10, 10, 0, tzinfo=IST).timestamp())
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="hold-10s",
        entry=100.0,
        stop=80.0,
        target=130.0,
        atm_strike=23200.0,
        opened_ts=opened,
        opened_bar=0,
        strike_source="TEST",
        limit_price=100.0,
        filled=True,
    )
    assert _exit_reason(pos, 101.0, opened + 20, 8, hold_bars=8) is None
    assert _exit_reason(pos, 101.0, opened + 8 * 60, 3, hold_bars=8) == "TIME"


def test_trend_pause_skips_9m_time() -> None:
    from desk_ml.paper_scalp import TIME_HARD_SEC, _exit_reason

    opened = int(datetime(2026, 9, 10, 10, 0, tzinfo=IST).timestamp())
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="trend-pause",
        entry=100.0,
        stop=80.0,
        target=130.0,
        atm_strike=23200.0,
        opened_ts=opened,
        opened_bar=0,
        strike_source="TEST",
        limit_price=100.0,
        filled=True,
        seen_high=118.0,
        seen_high_ts=opened + 60,
        premium_prints=[100.0 + i * 1.2 for i in range(16)],
    )
    classified = {"er": 0.42, "last3_impulse": "UP", "vol_expand": True}
    assert _exit_reason(pos, 117.0, opened + 8 * 60, 3, hold_bars=8, classified=classified) is None
    assert (
        _exit_reason(pos, 117.0, opened + int(TIME_HARD_SEC), 3, hold_bars=8, classified=classified)
        == "TIME"
    )


def test_logit_does_not_emit_ce_pe_on_first_session_3m_after_gap() -> None:
    from backtest_engine.ml_leans import lean_ml_logit
    from desk_ml.paper_scalp import resample_closes_3m

    closes: dict[int, float] = {}
    px = 22000.0
    for day in (15, 16):
        start = int(datetime(2026, 9, day, 9, 15, tzinfo=IST).timestamp())
        for i in range(125):
            px += 1.4
            closes[start + i * 180] = px
    today_open = int(datetime(2026, 9, 17, 9, 15, tzinfo=IST).timestamp())
    for i in range(8):
        px += 1.4
        closes[today_open + i * 180] = px
    bars = resample_closes_3m(closes)
    first_today = next(i for i, b in enumerate(bars) if b.ts >= today_open)
    leans = lean_ml_logit(bars, train_end_ts=today_open)
    assert leans[first_today] == "SKIP"
    later = leans[first_today + 1 : first_today + 6]
    assert any(s in {"CE", "PE", "SKIP"} for s in later)

    today_ticks = _ten_sec_trend(n=12)
    # Rebase 10s ticks onto 17 Sep 09:15 so they sit after the overnight gap.
    shift = today_open - today_ticks[0].ts
    today_ticks = [
        Triple(ts=t.ts + shift, idx_close=t.idx_close, ce_close=t.ce_close, pe_close=t.pe_close)
        for t in today_ticks
    ]
    series, _meta = logit_side_series(today_ticks, index_closes=closes, xr=False)
    assert series
    assert series[0].get("side") not in {"CE", "PE"}


def test_classify_needs_vwap_ema_and_blocks_shrinking_volume() -> None:
    trend = [25000.0 + i * 8.0 for i in range(40)]
    t = classify_index_regime(trend)
    assert t["regime"] == "TREND"
    assert t["direction"] == "UP"
    assert t["vwap"] is not None
    assert t["ema"] is not None
    assert t["ema_len"] in {15, 21}
    assert t["rsi"] is not None and t["rsi"] >= 55
    shrink = [1000.0] * 34 + [900.0, 800.0, 700.0, 600.0, 500.0, 400.0]
    blocked = classify_index_regime(trend, volumes=shrink)
    assert blocked["vol_expand"] is False
    assert blocked["last3_impulse_raw"] == "UP"
    assert blocked["last3_impulse"] is None
    assert blocked["last3_confirmed"] is False


def test_last3_put_impulse_beats_15m_chop() -> None:
    chop = [25000.0 + (4.0 if i % 2 == 0 else -4.0) for i in range(37)]
    dump = chop + [24990.0, 24970.0, 24940.0]
    expand = [100.0] * 37 + [180.0, 220.0, 260.0]
    t = classify_index_regime(dump, volumes=expand)
    assert t["regime"] == "TREND"
    assert t["direction"] == "DOWN"
    assert t["last3_impulse"] == "DOWN"
    assert t["last3_confirmed"] is True
    still_chop = chop + [25004.0, 24996.0, 25004.0]
    s = classify_index_regime(still_chop)
    assert s["regime"] == "SIDEWAYS"
    assert s["last3_impulse"] is None
    shrink = [1000.0] * 34 + [900.0, 800.0, 700.0, 600.0, 500.0, 400.0]
    blocked = classify_index_regime(dump, volumes=shrink)
    assert blocked["last3_impulse_raw"] == "DOWN"
    assert blocked["last3_impulse"] is None
    sensex = [74650.0 + (3.0 if i % 2 == 0 else -3.0) for i in range(20)]
    sensex += [74519.0, 74416.0, 74352.0]
    sx = classify_index_regime(sensex, volumes=shrink)
    assert sx["last3_net"] is not None and abs(float(sx["last3_net"])) >= 90
    assert sx["last3_impulse"] is None


def test_last3_trap_shooting_star_and_pdl_bounce() -> None:
    from desk_ml.paper_scalp import candle_shape, confirm_last3_impulse, build_sr_levels

    star = {"open": 25010.0, "high": 25080.0, "low": 25008.0, "close": 25014.0}
    shape = candle_shape(star, prior_range=8.0)
    assert shape["shooting_star"] is True
    expand = [100.0] * 12 + [200.0]
    up = confirm_last3_impulse(
        impulse_dir="UP",
        last_bar=star,
        prior_range=8.0,
        volumes=expand,
        vol_expand=True,
    )
    assert up["ok"] is False
    hammer = {"open": 24940.0, "high": 24945.0, "low": 24870.0, "close": 24938.0}
    bounce = confirm_last3_impulse(
        impulse_dir="DOWN",
        last_bar=hammer,
        prior_range=12.0,
        volumes=expand,
        vol_expand=True,
        sr={"pdl": 24880.0},
    )
    assert bounce["ok"] is False
    strong = {"open": 24990.0, "high": 24992.0, "low": 24938.0, "close": 24940.0}
    ok = confirm_last3_impulse(
        impulse_dir="DOWN",
        last_bar=strong,
        prior_range=12.0,
        volumes=expand,
        vol_expand=True,
        opt_confirm={"ce_chg": -2.0, "pe_chg": 4.0},
    )
    assert ok["ok"] is True
    ts0 = _ts(0)
    hist = {ts0 - 86400: 25100.0, ts0 - 86400 + 60: 24900.0, ts0: 25000.0}
    sr = build_sr_levels(hist, session_ist_date="2026-09-10")
    assert sr["pdh"] == 25100.0
    assert sr["pdl"] == 24900.0


def test_impulse_pause_then_volume_continue() -> None:
    from desk_ml.paper_scalp import apply_impulse_pause_continue

    engine = BookEngine()
    first = {
        "last3_impulse_raw": "DOWN",
        "last3_impulse": "DOWN",
        "last3_confirmed": True,
        "last3_net": -50.0,
        "regime": "TREND",
        "direction": "DOWN",
        "candle_shape": "strong_down",
    }
    a = apply_impulse_pause_continue(engine, "NIFTY", first, _ts(0))
    assert a["last3_impulse"] is None
    pause = {
        "last3_impulse_raw": None,
        "last3_impulse": None,
        "last3_confirmed": False,
        "regime": "SIDEWAYS",
        "candle_shape": "doji",
    }
    b = apply_impulse_pause_continue(engine, "NIFTY", pause, _ts(1))
    assert engine.impulse_pending["NIFTY"]["pause_seen"] is True
    cont = {
        "last3_impulse_raw": "DOWN",
        "last3_impulse": "DOWN",
        "last3_confirmed": True,
        "regime": "SIDEWAYS",
        "direction": "FLAT",
        "candle_shape": "strong_down",
    }
    c = apply_impulse_pause_continue(engine, "NIFTY", cont, _ts(2))
    assert c["last3_impulse"] == "DOWN"
    assert c["last3_reason"] == "pause_continue"


def test_sensex_does_not_use_banknifty_continuation_gate() -> None:
    from desk_ml.paper_scalp import _try_open

    engine = BookEngine(skip_bn_unless_last3=True)
    engine.last_regime["SENSEX"] = {
        "regime": "TREND",
        "direction": "DOWN",
        "last3_impulse": None,
        "itm_bin": {"side": "PE"},
    }
    tick = Triple(ts=_ts(10), idx_close=74000.0, ce_close=100.0, pe_close=140.0, atm_strike=74000.0)
    _try_open(
        engine,
        book_id="MIX-ML-LOGIT",
        underlying="SENSEX",
        side="PE",
        tick=tick,
        ce_path=[100.0],
        pe_path=[140.0],
        bar_i=10,
    )
    assert not any(s.get("reason") == "WIDE_WAIT_CONTINUATION" for s in engine.skips)
    assert any(s.get("reason") == "SENSEX_WAIT_STRENGTH" for s in engine.skips)


def test_index_point_profiles_nifty_tight_sensex_wide() -> None:
    from desk_ml.paper_scalp import propose_levels

    path_n = [98.0, 99.0, 100.0, 101.0, 102.5, 101.5, 100.5]
    n = propose_levels(100.0, path_n, underlying="NIFTY")
    assert n["ok"] is True
    assert n["unit"] == "premium_points"
    assert 6.0 - 1e-9 <= n["entry"] - n["stop"] <= 18.0 + 1e-9
    path_s = [430.0, 438.0, 450.0, 462.0, 455.0, 448.0, 460.0]
    s = propose_levels(450.0, path_s, underlying="SENSEX")
    assert s["ok"] is True
    assert s["entry"] - s["stop"] >= 18.0 - 1e-9
    assert s["entry"] - s["stop"] <= 42.0 + 1e-9
    assert (s["entry"] - s["stop"]) > (n["entry"] - n["stop"])


def test_skip_banknifty_focus_nifty_sensex(tmp_path) -> None:
    from desk_ml.founder_session import save_founder_book
    from desk_ml.paper_scalp import _try_open

    save_founder_book(["NIFTY", "BANKNIFTY", "SENSEX"], root=tmp_path)
    engine = BookEngine(skip_banknifty=True, root=tmp_path)
    engine.last_regime["BANKNIFTY"] = {"regime": "TREND", "direction": "UP", "itm_bin": {"side": "CE"}}
    tick = Triple(ts=_ts(10), idx_close=52000.0, ce_close=200.0, pe_close=180.0, atm_strike=52000.0)
    _try_open(
        engine,
        book_id="MIX-ML-LOGIT",
        underlying="BANKNIFTY",
        side="CE",
        tick=tick,
        ce_path=[200.0],
        pe_path=[180.0],
        bar_i=10,
    )
    assert engine.has_open("MIX-ML-LOGIT", "BANKNIFTY") is False
    assert any(s.get("reason") == "FOCUS_NIFTY_SENSEX" for s in engine.skips)


def test_skip_sensex_focus_nifty_only(tmp_path) -> None:
    from desk_ml.founder_session import save_founder_book
    from desk_ml.paper_scalp import _try_open

    save_founder_book(["NIFTY", "BANKNIFTY", "SENSEX"], root=tmp_path)
    engine = BookEngine(skip_sensex=True, sensex_need_strength=False, root=tmp_path)
    engine.last_regime["SENSEX"] = {"regime": "TREND", "direction": "UP", "last3_impulse": "UP"}
    tick = Triple(ts=_ts(10), idx_close=74300.0, ce_close=300.0, pe_close=280.0, atm_strike=74300.0)
    _try_open(
        engine,
        book_id="MIX-ML-LOGIT",
        underlying="SENSEX",
        side="CE",
        tick=tick,
        ce_path=[300.0],
        pe_path=[280.0],
        bar_i=10,
    )
    assert engine.has_open("MIX-ML-LOGIT", "SENSEX") is False
    assert any(s.get("reason") == "FOCUS_NIFTY_ONLY" for s in engine.skips)


def test_nifty_pe_filter_skips_ce() -> None:
    from desk_ml.paper_scalp import _try_open

    engine = BookEngine(nifty_allow_sides=("PE",))
    engine.last_regime["NIFTY"] = {"regime": "TREND", "direction": "UP", "itm_bin": {"side": "CE"}, "last3_impulse": "UP"}
    tick = Triple(ts=_ts(10), idx_close=23200.0, ce_close=120.0, pe_close=80.0, atm_strike=23200.0)
    _try_open(
        engine,
        book_id="MIX-ML-LOGIT",
        underlying="NIFTY",
        side="CE",
        tick=tick,
        ce_path=[120.0],
        pe_path=[80.0],
        bar_i=10,
    )
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is False
    assert any(s.get("reason") == "NIFTY_SIDE_FILTER" for s in engine.skips)


def test_nifty_ce_opens_on_up_strength_when_both_wings_allowed() -> None:
    from desk_ml.paper_scalp import _try_open

    engine = BookEngine(
        nifty_allow_sides=("CE", "PE"),
        nifty_need_strength=True,
        nifty_align_impulse=True,
    )
    engine.last_regime["NIFTY"] = {
        "regime": "TREND",
        "direction": "UP",
        "itm_bin": {"side": "CE", "ce_votes": ["CE_SHORT_COVER"], "pe_votes": []},
        "last3_impulse": "UP",
        "last3_reason": "pause_continue",
    }
    tick = Triple(
        ts=_ts(10),
        idx_close=23200.0,
        ce_close=120.0,
        pe_close=80.0,
        atm_strike=23200.0,
        itm_ce_close=160.0,
        itm_ce_strike=23000.0,
        wing_quotes={
            "23000": {"ce": 160.0, "pe": 20.0},
            "23200": {"ce": 120.0, "pe": 80.0},
            "23400": {"ce": 20.0, "pe": 140.0},
        },
    )
    _try_open(
        engine,
        book_id="MIX-ML-LOGIT",
        underlying="NIFTY",
        side="CE",
        tick=tick,
        ce_path=[120.0],
        pe_path=[80.0],
        bar_i=10,
    )
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is True
    pos = engine.opens[("MIX-ML-LOGIT", "NIFTY")]
    assert pos.side == "CE"
    _try_open(
        engine,
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="PE",
        tick=tick,
        ce_path=[120.0],
        pe_path=[80.0],
        bar_i=10,
    )
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert any(s.get("reason") in {"TREND_UP_KILL_PE", "NIFTY_IMPULSE_ALIGN", "BIN_SIDE_MISMATCH"} for s in engine.skips)


def test_nifty_impulse_align_skips_ce_on_last3_down() -> None:
    from desk_ml.paper_scalp import _try_open

    engine = BookEngine(nifty_align_impulse=True, skip_trend_against=False)
    engine.last_regime["NIFTY"] = {
        "regime": "TREND",
        "direction": "DOWN",
        "itm_bin": {"side": "CE"},
        "last3_impulse": "DOWN",
    }
    tick = Triple(ts=_ts(10), idx_close=23200.0, ce_close=120.0, pe_close=80.0, atm_strike=23200.0)
    _try_open(
        engine,
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        tick=tick,
        ce_path=[120.0],
        pe_path=[80.0],
        bar_i=10,
    )
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert any(s.get("reason") == "NIFTY_IMPULSE_ALIGN" for s in engine.skips)


def test_nifty_skip_side_after_stop() -> None:
    from desk_ml.paper_scalp import _try_open

    engine = BookEngine(nifty_skip_side_after_stop=True)
    engine.last_stop_side_by_und["NIFTY"] = {"CE": _ts(8)}
    engine.last_regime["NIFTY"] = {
        "regime": "TREND",
        "direction": "UP",
        "itm_bin": {"side": "CE"},
        "last3_impulse": "UP",
    }
    tick = Triple(ts=_ts(10), idx_close=23200.0, pe_close=80.0, ce_close=120.0, atm_strike=23200.0)
    _try_open(
        engine,
        book_id="MIX-ML-LOGIT",
        underlying="NIFTY",
        side="CE",
        tick=tick,
        ce_path=[120.0],
        pe_path=[80.0],
        bar_i=10,
    )
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is False
    assert any(s.get("reason") == "NIFTY_SIDE_AFTER_STOP" for s in engine.skips)


def test_nifty_skip_ce_after_stop() -> None:
    from desk_ml.paper_scalp import _try_open

    engine = BookEngine(nifty_skip_ce_after_stop=True)
    engine.last_stop_side_by_und["NIFTY"] = {"CE": _ts(8)}
    engine.last_regime["NIFTY"] = {
        "regime": "TREND",
        "direction": "UP",
        "itm_bin": {"side": "CE"},
        "last3_impulse": "UP",
    }
    tick = Triple(ts=_ts(10), idx_close=23200.0, ce_close=120.0, pe_close=80.0, atm_strike=23200.0)
    _try_open(
        engine,
        book_id="MIX-ML-LOGIT",
        underlying="NIFTY",
        side="CE",
        tick=tick,
        ce_path=[120.0],
        pe_path=[80.0],
        bar_i=10,
    )
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is False
    assert any(s.get("reason") == "NIFTY_CE_AFTER_STOP" for s in engine.skips)


def test_nifty_two_stop_halt() -> None:
    from desk_ml.paper_scalp import _try_open

    engine = BookEngine(nifty_halt_after_stops=2)
    engine.session_stop_count["NIFTY"] = 2
    engine.last_regime["NIFTY"] = {
        "regime": "TREND",
        "direction": "DOWN",
        "itm_bin": {"side": "PE"},
        "last3_impulse": "DOWN",
    }
    tick = Triple(ts=_ts(10), idx_close=23200.0, ce_close=80.0, pe_close=120.0, atm_strike=23200.0)
    _try_open(
        engine,
        book_id="MIX-ML-LOGIT",
        underlying="NIFTY",
        side="PE",
        tick=tick,
        ce_path=[80.0],
        pe_path=[120.0],
        bar_i=10,
    )
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is False
    assert any(s.get("reason") == "NIFTY_TWO_STOP_HALT" for s in engine.skips)


def test_unfilled_cancels_when_index_turns_sideways() -> None:
    engine = BookEngine()
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="working-sideways",
        entry=120.0,
        stop=80.0,
        target=140.0,
        atm_strike=25000.0,
        opened_ts=_ts(12) - 30,
        opened_bar=12,
        strike_source="TEST",
        limit_price=117.0,
        filled=False,
        index_regime="TREND",
    )
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos
    engine.last_regime["NIFTY"] = {"regime": "SIDEWAYS", "direction": "FLAT"}
    tick = Triple(ts=_ts(12), idx_close=25000.0, ce_close=118.0, pe_close=110.0)
    mark_to_market(engine, tick, "NIFTY", 12, index_regime="SIDEWAYS")
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert engine.closed and engine.closed[0]["exit_reason"] == "CANCEL_UNFILLED_SIDEWAYS"


def test_wipe_leaves_dual_tape_jsonl(tmp_path) -> None:
    from desk_ml.paper_scalp import wipe_today_paper_book
    from trading_agents_india.session_clock import IST as IST_TZ

    day = "2026-09-17"
    folder = tmp_path / "data" / "recon" / "paper_watch" / "DUAL-TAPE"
    folder.mkdir(parents=True)
    path = folder / f"{day}.jsonl"
    now = datetime(2026, 9, 17, 12, 0, tzinfo=IST_TZ)
    lines = []
    for i in range(40):
        ts = now.timestamp() - (40 - i) * 60
        dt = datetime.fromtimestamp(ts, tz=IST_TZ)
        lines.append(json.dumps({"as_of_ist": dt.isoformat(timespec="seconds"), "tick_index": i}))
    body = "\n".join(lines) + "\n"
    path.write_text(body, encoding="utf-8")
    (tmp_path / "data" / "recon" / "paper_ledger").mkdir(parents=True)
    out = wipe_today_paper_book(root=tmp_path, ist_date=day)
    assert out["ok"] is True
    assert path.read_text(encoding="utf-8") == body
    assert out["jsonl_keep"]["kept"] == "untouched"
    assert out.get("paper_book_epoch_ts")


def test_paper_book_epoch_does_not_replay_old_opens(tmp_path) -> None:
    from desk_ml.paper_scalp import DEFAULT_PAPER_PARAMS, replay_paper_scalp

    triples = _triples(n=40, trend=8.0)
    epoch = int(triples[25].ts)
    recon = tmp_path / "data" / "recon"
    recon.mkdir(parents=True)
    (recon / "ml_paper_session_params.json").write_text(
        json.dumps({**DEFAULT_PAPER_PARAMS, "paper_book_epoch_ts": epoch}),
        encoding="utf-8",
    )
    board = replay_paper_scalp(
        root=tmp_path,
        underlyings=("NIFTY",),
        triples_by_und={"NIFTY": triples},
        write=False,
        live_session=True,
        deny_model_signals=False,
    )
    for row in list(board.get("closed_trades") or []) + list(board.get("open_trades") or []):
        opened = int(row.get("opened_ts") or 0)
        assert opened >= epoch


def test_last3_impulse_owns_fill_side_not_10s_logit_bounce() -> None:
    from desk_ml.paper_scalp import resolve_fill_intents

    out = resolve_fill_intents(
        dealer_confirm=None,
        dealer_verdict="HOLD",
        logit={"side": "CE", "status": "OK"},
        logit_xr={"side": None, "status": "SKIP", "reason": "no xr"},
        ml001_hold=True,
        follow_gap=False,
        ml002_hold=True,
        ml1={"status": "DATA_INSUFFICIENT"},
        impulse_side="PE",
    )
    assert out["MIX-ML-LOGIT"] == ("PE", None)
    assert out["MIX-ML-GREEKS"] == (None, "GREEKS_NO_CLONE")
    assert out["MIX-DEFAULT-BUY"] == ("PE", None)


def test_seen_not_taken_section_explains_skip() -> None:
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
        logit={"side": "PE", "status": "OK"},
        logit_xr={"side": "PE", "status": "OK"},
        ml1={"status": "OK", "take": True},
        tv_side="PE",
        deny_model_signals=True,
    )
    seen = seen_not_taken_picture(engine)
    assert seen["observations"]
    assert any("NIFTY" in n for n in seen["observations"])
    assert seen["skipped_latest"]
    md = render_markdown(
        {
            "title": "LIVE SESSION",
            "today": {},
            "seen_not_taken": seen,
            "closed_trades": [],
            "open_trades": [],
        }
    )
    assert "## Seen but not taken / cancelled (why)" in md
    assert "SKIP" in md or "SIDEWAYS" in md


def _nifty_itm_wings(*, pe_px: float, ce_px: float, pe_vol: float, ce_vol: float, pe_oi: float | None, ce_oi: float | None, pe_delta: float = -0.55, ce_delta: float = 0.55) -> dict:
    cell_ce: dict = {"ce": ce_px, "ce_volume": ce_vol, "ce_delta": ce_delta}
    cell_pe: dict = {"pe": pe_px, "pe_volume": pe_vol, "pe_delta": pe_delta}
    if pe_oi is not None:
        cell_pe["pe_oi"] = pe_oi
    if ce_oi is not None:
        cell_ce["ce_oi"] = ce_oi
    return {
        "24800": cell_ce,
        "25000": {"ce": 120.0, "pe": 110.0},
        "25200": cell_pe,
    }


def test_itm_bin_two_votes_trend_without_three_index_bars() -> None:
    prev = {
        "ce": {"px": 140.0, "volume": 10000.0, "oi": 80000.0, "delta": 0.55},
        "pe": {"px": 150.0, "volume": 10000.0, "oi": 80000.0, "delta": -0.50},
    }
    curr = {
        "ce": {"px": 128.0, "volume": 13000.0, "oi": 79000.0, "delta": 0.50},
        "pe": {"px": 168.0, "volume": 16000.0, "oi": 86000.0, "delta": -0.58},
    }
    scored = score_itm_bin(prev, curr)
    assert scored["side"] == "PE"
    assert scored["wait_3_index_bars"] is False
    assert scored["n_pe_votes"] >= 2
    assert "PE_VOL_EXPAND" in scored["pe_votes"]
    assert "CE_PREMIUM_DOWN" in scored["pe_votes"]
    thin = score_itm_bin(
        {"ce": {"px": 140.0}, "pe": {"px": 150.0}},
        {"ce": {"px": 141.0}, "pe": {"px": 151.0}},
    )
    assert thin["side"] is None
    assert "ce_volume" in thin["missing"] or "pe_volume" in thin["missing"]
    prem_only = score_itm_bin(
        {"ce": {"px": 140.0, "volume": 10000.0}, "pe": {"px": 150.0, "volume": 10000.0}},
        {"ce": {"px": 148.0, "volume": 10010.0}, "pe": {"px": 142.0, "volume": 10010.0}},
    )
    assert prem_only["side"] is None
    assert "CE_PREMIUM_UP" in prem_only["ce_votes"]


def test_itm_bin_opens_pe_on_chop_index_without_last3() -> None:
    triples = _chop_triples(n=42)
    def _with_wings(t: Triple, pe_px: float, ce_px: float, pe_vol: float, ce_vol: float, pe_oi: float, ce_oi: float) -> Triple:
        atm = 25000.0
        return Triple(
            ts=t.ts,
            idx_close=t.idx_close,
            ce_close=ce_px,
            pe_close=pe_px,
            atm_strike=atm,
            itm_ce_close=ce_px,
            itm_pe_close=pe_px,
            itm_ce_strike=24800.0,
            itm_pe_strike=25200.0,
            wing_quotes=_nifty_itm_wings(
                pe_px=pe_px, ce_px=ce_px, pe_vol=pe_vol, ce_vol=ce_vol, pe_oi=pe_oi, ce_oi=ce_oi
            ),
        )

    triples[40] = _with_wings(triples[40], 150.0, 140.0, 10000.0, 10000.0, 80000.0, 80000.0)
    triples[41] = _with_wings(triples[41], 168.0, 128.0, 16000.0, 13000.0, 86000.0, 79000.0)
    engine = BookEngine(sod_one_ticket=False, picker_majority=False)
    kwargs = dict(
        underlying="NIFTY",
        triples=triples,
        ml001_hold=True,
        ml002_hold=True,
        follow_gap=True,
        logit={"side": "CE", "status": "OK"},
        logit_xr={"side": None, "status": "SKIP"},
        ml1={"status": "DATA_INSUFFICIENT"},
        tv_side="CE",
        deny_model_signals=True,
    )
    step_underlying(engine, i=40, **kwargs)
    step_underlying(engine, i=41, **kwargs)
    classified = engine.last_regime["NIFTY"]
    assert classified["regime"] == "TREND"
    assert classified["direction"] == "DOWN"
    assert classified["reason"] == "itm_bin_pe_confirm"
    assert classified["last3_impulse"] is None
    pos = engine.opens.get(("MIX-ML-LOGIT", "NIFTY"))
    assert pos is not None
    assert pos.side == "PE"
    assert pos.atm_strike == 25200.0
    assert pos.strike_source == "ITM_100"
    assert pos.filled is True
    pic = itm_bins_picture(engine)
    assert pic["bins"][0]["side"] == "PE"
    md = render_markdown({"title": "LIVE SESSION", "today": {}, "itm_bins": pic, "seen_not_taken": {}, "closed_trades": [], "open_trades": []})
    assert "## ITM CE / PE bin (three charts)" in md


def test_cancel_bin_roll_when_itm_becomes_atm() -> None:
    pos = OpenPaper(
        book_id="MIX-ML-LOGIT",
        underlying="NIFTY",
        side="PE",
        trade_id="bin-roll",
        entry=160.0,
        stop=140.0,
        target=200.0,
        atm_strike=25100.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="ITM_100",
        limit_price=160.0,
        filled=True,
        idx_at_open=25000.0,
    )
    still_itm = Triple(ts=_ts(1), idx_close=24980.0, ce_close=100.0, pe_close=170.0, atm_strike=25000.0)
    assert cancel_if_bin_rolled(pos, still_itm) is None
    now_atm = Triple(ts=_ts(2), idx_close=25100.0, ce_close=130.0, pe_close=155.0, atm_strike=25100.0)
    assert cancel_if_bin_rolled(pos, now_atm) == CANCEL_BIN_ROLL
    engine = BookEngine()
    engine.opens[("MIX-ML-LOGIT", "NIFTY")] = pos
    mark_to_market(engine, now_atm, "NIFTY", 2, atm_strike=25100.0)
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is True
    kept = engine.opens[("MIX-ML-LOGIT", "NIFTY")]
    assert kept.stop == 140.0
    assert kept.path_stop in {None, 140.0}


def test_filled_thesis_flip_flattens_not_soft_trail() -> None:
    from desk_ml.paper_scalp import trail_premium_band

    assert TRAIL_BAND_MIN <= trail_premium_band() <= TRAIL_BAND_MAX
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="SENSEX",
        side="CE",
        trade_id="thesis-hard",
        entry=297.45,
        stop=280.5,
        target=325.0,
        atm_strike=74300.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="TEST",
        limit_price=297.45,
        lot_size=20,
        lots=1,
        qty=20,
        filled=True,
        last_ltp=290.0,
        path_stop=280.5,
    )
    engine = BookEngine()
    engine.opens[("MIX-DEFAULT-BUY", "SENSEX")] = pos
    tick = Triple(ts=_ts(2), idx_close=74350.0, ce_close=290.0, pe_close=180.0, atm_strike=74300.0)
    mark_to_market(engine, tick, "SENSEX", 2, atm_strike=74300.0, dealer_verdict="BUY_PE_CONFIRM")
    assert engine.has_open("MIX-DEFAULT-BUY", "SENSEX") is False
    assert engine.closed[-1]["exit_reason"] == "CANCEL_THESIS"


def test_strict_target_flattens_without_shift() -> None:
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="target-strict",
        entry=100.0,
        stop=80.0,
        target=120.0,
        atm_strike=23200.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="TEST",
        limit_price=100.0,
        lot_size=65,
        lots=1,
        qty=65,
        filled=True,
        last_ltp=121.0,
        path_stop=80.0,
    )
    engine = BookEngine()
    assert engine.apply_target_shift is False
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos
    tick = Triple(ts=_ts(2), idx_close=23250.0, ce_close=121.0, pe_close=80.0, atm_strike=23200.0)
    mark_to_market(engine, tick, "NIFTY", 2, atm_strike=23200.0)
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert engine.closed[-1]["exit_reason"] == "TARGET"


def test_target_lock_shift_only_when_flag_on() -> None:
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="target-lock",
        entry=100.0,
        stop=80.0,
        target=120.0,
        atm_strike=23200.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="TEST",
        limit_price=100.0,
        lot_size=65,
        lots=1,
        qty=65,
        filled=True,
        last_ltp=121.0,
        path_stop=80.0,
    )
    engine = BookEngine(apply_target_shift=True)
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos
    tick = Triple(ts=_ts(2), idx_close=23250.0, ce_close=121.0, pe_close=80.0, atm_strike=23200.0)
    mark_to_market(engine, tick, "NIFTY", 2, atm_strike=23200.0)
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is True
    later = Triple(ts=_ts(4), idx_close=23250.0, ce_close=122.0, pe_close=80.0, atm_strike=23200.0)
    mark_to_market(engine, later, "NIFTY", 4, atm_strike=23200.0)
    kept = engine.opens[("MIX-DEFAULT-BUY", "NIFTY")]
    from desk_ml.groww_costs import breakeven_premium

    be = breakeven_premium(entry=100.0, qty=65)
    assert kept.stop >= be
    assert kept.target > 120.0
    assert kept.target_step == 1
    assert kept.agent_status.startswith("TARGET_STEP")


def test_hard_stop_still_flattens() -> None:
    pos = OpenPaper(
        book_id="MIX-ML-LOGIT",
        underlying="NIFTY",
        side="PE",
        trade_id="hard-stop",
        entry=160.0,
        stop=140.0,
        target=200.0,
        atm_strike=25100.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="ITM_100",
        limit_price=160.0,
        filled=True,
        last_ltp=139.0,
        path_stop=140.0,
    )
    engine = BookEngine()
    engine.opens[("MIX-ML-LOGIT", "NIFTY")] = pos
    tick = Triple(ts=_ts(2), idx_close=25100.0, ce_close=130.0, pe_close=139.0, pe_low=139.0, atm_strike=25100.0)
    mark_to_market(engine, tick, "NIFTY", 2, atm_strike=25100.0)
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is False
    assert engine.closed[-1]["exit_reason"] == "STOP"


def test_unfilled_still_cancels_zero_rupee() -> None:
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="unfilled-away",
        entry=100.0,
        stop=80.0,
        target=130.0,
        atm_strike=23200.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="TEST",
        limit_price=98.8,
        filled=False,
        last_ltp=100.0,
    )
    engine = BookEngine()
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos
    tick = Triple(ts=_ts(3), idx_close=23250.0, ce_close=110.0, pe_close=80.0, atm_strike=23200.0)
    mark_to_market(engine, tick, "NIFTY", 3, atm_strike=23200.0)
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    row = engine.closed[-1]
    assert str(row["exit_reason"]).startswith("CANCEL_UNFILLED")
    assert row["status"] == "CANCELLED_UNFILLED"
    assert row["charges_inr"] == 0.0


def test_floor_path_stop_clears_chop() -> None:
    from desk_ml.paper_scalp import floor_path_stop, propose_levels

    assert floor_path_stop(entry=100.0, stop=97.0) <= 92.0
    levels = propose_levels(100.0, [98.0, 99.0, 100.0, 101.0, 102.0])
    assert levels["entry"] - levels["stop"] >= 8.0 - 1e-9


def test_bin_side_mismatch_and_short_cover_votes() -> None:
    from desk_ml.paper_scalp import bin_side_allows, score_itm_bin

    classified = {"itm_bin": {"side": "PE"}, "last3_impulse": None}
    assert bin_side_allows(classified, "PE") is True
    assert bin_side_allows(classified, "CE") is False
    classified["last3_impulse"] = "UP"
    assert bin_side_allows(classified, "CE") is True
    prev = {
        "pe": {"px": 100.0, "oi": 2000.0, "volume": 10.0, "delta": -0.4},
        "ce": {"px": 110.0, "oi": 2000.0, "volume": 10.0, "delta": 0.4},
    }
    curr = {
        "pe": {"px": 108.0, "oi": 1800.0, "volume": 12.0, "delta": -0.45},
        "ce": {"px": 104.0, "oi": 2100.0, "volume": 11.0, "delta": 0.38},
    }
    scored = score_itm_bin(prev, curr)
    assert "PE_SHORT_COVER" in scored["pe_votes"]
    unwind_curr = {
        "pe": {"px": 92.0, "oi": 1700.0, "volume": 12.0, "delta": -0.35},
        "ce": {"px": 118.0, "oi": 1700.0, "volume": 11.0, "delta": 0.42},
    }
    unwound = score_itm_bin(prev, unwind_curr)
    assert "PE_LONG_UNWIND" in unwound["pe_votes"]
    from desk_ml.paper_scalp import covering_label

    assert covering_label({"itm_bin": unwound}, "PE") == "LONG_UNWIND"


def test_cover_long_unwind_books_after_t1() -> None:
    from desk_ml.paper_scalp import COVER_LONG_UNWIND

    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="PE",
        trade_id="cover-unwind",
        entry=100.0,
        stop=92.0,
        target=140.0,
        atm_strike=23350.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="ITM_100",
        limit_price=100.0,
        lot_size=65,
        lots=1,
        qty=65,
        filled=True,
        last_ltp=112.0,
        path_stop=92.0,
        target_step=1,
        agent_status="TARGET_STEP_1",
    )
    engine = BookEngine()
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos
    engine.last_regime["NIFTY"] = {
        "itm_bin": {"side": "PE", "pe_votes": ["PE_LONG_UNWIND"], "ce_votes": []}
    }
    tick = Triple(ts=_ts(2), idx_close=23250.0, ce_close=80.0, pe_close=112.0, atm_strike=23300.0)
    mark_to_market(engine, tick, "NIFTY", 2, atm_strike=23300.0)
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert engine.closed[-1]["exit_reason"] == COVER_LONG_UNWIND


def test_stall_books_stale_high_low_er() -> None:
    from desk_ml.paper_scalp import CANCEL_STALL, STALL_HIGH_STALE_SEC, STALL_MIN_SEC, stall_book_reason

    opened = int(datetime(2026, 9, 10, 10, 0, tzinfo=IST).timestamp())
    chop = []
    px = 150.0
    for i in range(16):
        px = 150.0 + (4.0 if i % 2 == 0 else -3.5)
        chop.append(px)
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="stall-ce",
        entry=149.7,
        stop=136.65,
        target=169.27,
        atm_strike=23250.0,
        opened_ts=opened,
        opened_bar=0,
        strike_source="TEST",
        limit_price=149.7,
        filled=True,
        seen_high=157.7,
        seen_high_ts=opened + 12 * 60,
        premium_prints=chop,
    )
    ts = opened + int(STALL_MIN_SEC) + int(STALL_HIGH_STALE_SEC) + 60
    classified = {"er": 0.05, "last3_impulse": None, "vol_expand": False}
    assert stall_book_reason(pos, 157.4, ts, classified=classified) == CANCEL_STALL
    assert stall_book_reason(pos, 152.0, ts, classified=classified) == CANCEL_STALL
    assert stall_book_reason(pos, 125.0, ts, classified=classified) is None
    pos_trend = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="stall-trend",
        entry=149.7,
        stop=136.65,
        target=169.27,
        atm_strike=23250.0,
        opened_ts=opened,
        opened_bar=0,
        strike_source="TEST",
        limit_price=149.7,
        filled=True,
        seen_high=157.7,
        seen_high_ts=opened + 12 * 60,
        premium_prints=chop,
    )
    assert (
        stall_book_reason(
            pos_trend,
            152.0,
            ts,
            classified={"er": 0.40, "last3_impulse": "UP", "vol_expand": True},
        )
        is None
    )


def test_greeks_soft_trail_does_not_block_stall() -> None:
    from desk_ml.paper_scalp import CANCEL_STALL, STALL_HIGH_STALE_SEC, STALL_MIN_SEC

    opened = int(datetime(2026, 9, 10, 10, 0, tzinfo=IST).timestamp())
    chop = [150.0 + (3.0 if i % 2 == 0 else -2.8) for i in range(16)]
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="greeks-stall",
        entry=149.7,
        stop=136.65,
        path_stop=136.65,
        target=169.27,
        atm_strike=23250.0,
        opened_ts=opened,
        opened_bar=0,
        strike_source="TEST",
        limit_price=149.7,
        lot_size=65,
        lots=1,
        qty=65,
        filled=True,
        last_ltp=152.0,
        seen_low=141.1,
        seen_high=157.7,
        seen_high_ts=opened + 12 * 60,
        premium_prints=chop,
    )
    engine = BookEngine()
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos
    engine.last_regime["NIFTY"] = {
        "er": 0.05,
        "last3_impulse": None,
        "vol_expand": False,
        "regime": "TREND",
    }
    ts = opened + int(STALL_MIN_SEC) + int(STALL_HIGH_STALE_SEC) + 120
    tick = Triple(ts=ts, idx_close=23325.0, ce_close=152.0, pe_close=160.0, atm_strike=23250.0)
    mark_to_market(engine, tick, "NIFTY", 40, atm_strike=23300.0, dealer_verdict="BUY_PE_CONFIRM")
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert engine.closed[-1]["exit_reason"] == CANCEL_STALL
    assert engine.closed[-1]["result"] == "STALL"


def test_pe_does_not_sit_call_rally() -> None:
    from desk_ml.paper_scalp import (
        CANCEL_AGAINST,
        COVER_LONG_UNWIND,
        _exit_reason,
        _trend_continuation,
        apply_itm_bin_to_regime,
        is_soft_cancel_reason,
        ticket_against_market,
    )

    pe = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="PE",
        trade_id="pe-vs-call",
        entry=128.0,
        stop=110.0,
        path_stop=110.0,
        target=150.5,
        atm_strike=23400.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="ITM_100",
        limit_price=128.0,
        lot_size=65,
        lots=10,
        qty=650,
        filled=True,
        last_ltp=116.6,
        seen_low=114.4,
        seen_high=138.35,
        seen_high_ts=_ts(1),
        target_step=0,
    )
    classified = {
        "regime": "TREND",
        "direction": "DOWN",
        "index_direction": "UP",
        "er": 0.64,
        "votes_up": 5,
        "votes_down": 0,
        "vol_expand": True,
        "last3_impulse": None,
        "last3_impulse_raw": "UP",
        "last3_confirmed": False,
        "last3_trap": "wait_pause",
        "itm_bin": {
            "side": "PE",
            "pe_votes": ["PE_PREMIUM_UP"],
            "ce_votes": ["CE_PREMIUM_UP", "PE_PREMIUM_DOWN", "CE_SHORT_COVER"],
        },
    }
    assert ticket_against_market(pe, classified) is True
    assert _trend_continuation(pe, classified=classified) is False
    assert _exit_reason(pe, 116.6, _ts(20), 20, classified=classified) == CANCEL_AGAINST
    assert is_soft_cancel_reason(CANCEL_AGAINST) is False
    assert is_soft_cancel_reason("CANCEL_THESIS") is False

    kept = apply_itm_bin_to_regime(
        {
            "regime": "TREND",
            "direction": "UP",
            "index_direction": "UP",
            "er": 0.64,
            "votes_up": 5,
            "votes_down": 0,
            "last3_impulse": None,
            "last3_impulse_raw": "UP",
        },
        {"side": "PE", "reason": "itm_bin_pe_confirm", "pe_votes": ["PE_PREMIUM_UP"], "ce_votes": []},
    )
    assert kept["direction"] == "UP"
    assert kept["itm_bin"]["side"] == "PE"

    chop_bin = apply_itm_bin_to_regime(
        {
            "regime": "SIDEWAYS",
            "direction": "FLAT",
            "er": 0.05,
            "votes_up": 1,
            "votes_down": 1,
            "last3_impulse": None,
            "last3_impulse_raw": None,
        },
        {"side": "PE", "reason": "itm_bin_pe_confirm", "pe_votes": ["PE_PREMIUM_UP"], "ce_votes": []},
    )
    assert chop_bin["regime"] == "TREND"
    assert chop_bin["direction"] == "DOWN"

    ce = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="ce-same-wing",
        entry=149.7,
        stop=136.65,
        target=169.27,
        atm_strike=23250.0,
        opened_ts=_ts(0),
        opened_bar=0,
        strike_source="TEST",
        limit_price=149.7,
        filled=True,
        seen_high=157.7,
    )
    assert _trend_continuation(
        ce, classified={"er": 0.40, "last3_impulse": "UP", "last3_impulse_raw": "UP", "direction": "UP"}
    ) is True

    engine = BookEngine()
    pos2 = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="PE",
        trade_id="pe-unwind",
        entry=128.0,
        stop=110.0,
        path_stop=110.0,
        target=150.5,
        atm_strike=23400.0,
        opened_ts=_ts(0),
        opened_bar=1,
        strike_source="ITM_100",
        limit_price=128.0,
        lot_size=65,
        lots=10,
        qty=650,
        filled=True,
        last_ltp=116.0,
        target_step=0,
    )
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos2
    engine.last_regime["NIFTY"] = {
        "regime": "TREND",
        "direction": "UP",
        "itm_bin": {
            "side": "CE",
            "pe_votes": ["PE_LONG_UNWIND"],
            "ce_votes": ["CE_PREMIUM_UP", "CE_OI_UP_WITH_PREMIUM"],
        },
    }
    tick = Triple(ts=_ts(8), idx_close=23355.0, ce_close=157.0, pe_close=116.0, atm_strike=23350.0)
    mark_to_market(engine, tick, "NIFTY", 8, atm_strike=23350.0, dealer_verdict="BUY_CE_CONFIRM")
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert engine.closed[-1]["exit_reason"] in {COVER_LONG_UNWIND, CANCEL_AGAINST, "CANCEL_THESIS"}

    green = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="ce-green-flicker",
        entry=149.7,
        stop=136.65,
        target=169.27,
        atm_strike=23250.0,
        opened_ts=_ts(0),
        opened_bar=0,
        strike_source="TEST",
        limit_price=149.7,
        filled=True,
        last_ltp=157.0,
        seen_high=157.7,
    )
    assert (
        ticket_against_market(
            green,
            {
                "er": 0.05,
                "last3_impulse_raw": "DOWN",
                "last3_impulse": None,
                "direction": "UP",
                "votes_up": 2,
                "votes_down": 1,
            },
            ltp=157.0,
        )
        is False
    )


def test_fix_first_chop_books_near_target() -> None:
    from desk_ml.paper_scalp import STALL_MIN_SEC_CHOP, propose_levels, stall_book_reason

    opened = int(datetime(2026, 9, 10, 10, 0, tzinfo=IST).timestamp())
    chop = [150.0 + (2.0 if i % 2 == 0 else -1.8) for i in range(16)]
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="chop-book",
        entry=149.7,
        stop=136.65,
        target=169.27,
        atm_strike=23250.0,
        opened_ts=opened,
        opened_bar=0,
        strike_source="TEST",
        limit_price=149.7,
        filled=True,
        seen_high=157.7,
        seen_high_ts=opened + 4 * 60,
        premium_prints=chop,
    )
    ts = opened + int(STALL_MIN_SEC_CHOP) + 4 * 60
    classified = {"er": 0.05, "last3_impulse": None, "vol_expand": False}
    assert stall_book_reason(pos, 157.4, ts, classified=classified) == "CANCEL_STALL"
    lv = propose_levels(
        149.7,
        [140.0, 145.0, 149.7],
        underlying="NIFTY",
        classified={"er": 0.05, "regime": "TREND"},
    )
    assert lv["ok"] is True
    assert float(lv["target"]) - 149.7 <= 10.01
    trend = propose_levels(
        153.0,
        [140.0, 150.0, 160.0, 170.0, 153.0],
        underlying="NIFTY",
        classified={"er": 0.40, "regime": "TREND", "direction": "DOWN", "last3_impulse": "DOWN"},
    )
    assert float(trend["target"]) - 153.0 > 10.0


def test_trend_retracement_does_not_stall() -> None:
    """Same-wing TREND ER≥0.35 is a retracement hold, not STALL. Prior-day overlay."""
    from desk_ml.paper_scalp import STALL_MIN_SEC_CHOP, stall_book_reason

    opened = int(datetime(2026, 9, 10, 10, 0, tzinfo=IST).timestamp())
    pos = OpenPaper(
        book_id="MIX-ML-LOGIT",
        underlying="NIFTY",
        side="CE",
        trade_id="retrace-hold",
        entry=203.0,
        stop=180.0,
        target=250.0,
        atm_strike=23700.0,
        opened_ts=opened,
        opened_bar=0,
        strike_source="TEST",
        limit_price=203.0,
        filled=True,
        seen_high=245.0,
        seen_high_ts=opened + 6 * 60,
        premium_prints=[203.0, 220.0, 245.0, 230.0, 220.0],
    )
    ts = opened + int(STALL_MIN_SEC_CHOP) + 6 * 60
    hold = {
        "er": 0.42,
        "last3_impulse": "UP",
        "vol_expand": True,
        "regime": "TREND",
        "direction": "UP",
    }
    assert stall_book_reason(pos, 220.0, ts, classified=hold) is None


def test_market_kind_labels() -> None:
    from desk_ml.paper_scalp import market_kind

    assert market_kind({"er": 0.42, "flip_frac": 0.2, "range_over_atr": 6.0}) == "TRENDING"
    assert market_kind({"er": 0.08, "flip_frac": 0.10, "range_over_atr": 2.0}) == "SIDEWAYS"
    assert market_kind({"er": 0.08, "flip_frac": 0.45, "range_over_atr": 2.0}) == "CHOPPY"
    assert market_kind({"er": 0.12, "flip_frac": 0.20, "range_over_atr": 8.0}) == "VOLATILE"
    assert market_kind({"regime": "TREND", "er": 0.05, "flip_frac": 0.10, "range_over_atr": 2.0}) == "SIDEWAYS"
    # itm_bin TREND + lunch ER ~0.05 is chop, not trend
    assert (
        market_kind(
            {
                "regime": "TREND",
                "reason": "itm_bin_ce_confirm",
                "er": 0.05,
                "flip_frac": 0.42,
                "range_over_atr": 2.0,
                "itm_bin": {"side": "CE"},
            }
        )
        == "CHOPPY"
    )
    assert market_kind({"regime": "TREND", "itm_bin": {"side": "CE"}}, require_er=True) == "UNKNOWN"


def test_close_stamps_open_and_exit_kind() -> None:
    from desk_ml.paper_scalp import _close

    engine = BookEngine()
    engine.last_regime["NIFTY"] = {
        "er": 0.08,
        "flip_frac": 0.40,
        "range_over_atr": 2.0,
        "regime": "TREND",
        "reason": "itm_bin_ce_confirm",
    }
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="kind-stamp",
        entry=203.0,
        stop=180.0,
        target=250.0,
        atm_strike=23700.0,
        opened_ts=_ts(10),
        opened_bar=10,
        strike_source="TEST",
        limit_price=203.0,
        filled=True,
        lot_size=65,
        lots=1,
        index_regime="TREND",
        regime_er=0.42,
        regime_flip_frac=0.1,
        market_kind_open="TRENDING",
    )
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos
    engine.equity["MIX-DEFAULT-BUY"] = 570000.0
    _close(engine, pos, ltp=220.0, ts=_ts(40), reason="CANCEL_STALL")
    row = engine.closed[-1]
    assert row["market_kind_open"] == "TRENDING"
    assert row["market_kind_close"] == "CHOPPY"
    from desk_ml.paper_scalp import skill_from_closed

    skill = skill_from_closed([row])
    assert skill["fills_by_kind"]["TRENDING"] == 1
    assert skill["exits_by_kind"]["CHOPPY"]["CANCEL_STALL"] == 1
    assert skill["n_stall_trending_open"] == 1
    assert any("TRENDING-at-open" in x for x in skill["lessons"])


def test_nifty_bin_confirm_counts_as_strength() -> None:
    from desk_ml.paper_scalp import nifty_has_entry_strength, _try_open

    pause_wait = {
        "regime": "TREND",
        "direction": "UP",
        "reason": "itm_bin_ce_confirm",
        "last3_impulse": None,
        "last3_reason": "wait_pause_after_impulse",
        "itm_bin": {"side": "CE", "ce_votes": ["CE_PREMIUM_UP"], "pe_votes": []},
    }
    assert nifty_has_entry_strength(pause_wait, "CE") is True
    assert nifty_has_entry_strength({"last3_impulse": None, "reason": "chop"}, "CE") is False
    assert nifty_has_entry_strength(
        {"regime": "TREND", "direction": "UP", "er": 0.36, "last3_impulse": None, "reason": "er_vwap_ema_vol_rsi"},
        "CE",
    ) is True

    engine = BookEngine(nifty_need_strength=True, nifty_allow_sides=("CE", "PE"))
    engine.last_regime["NIFTY"] = pause_wait
    tick = Triple(
        ts=_ts(10),
        idx_close=23367.0,
        ce_close=120.0,
        pe_close=80.0,
        atm_strike=23350.0,
        itm_ce_close=160.0,
        itm_ce_strike=23150.0,
        wing_quotes={
            "23150": {"ce": 160.0, "pe": 20.0},
            "23350": {"ce": 120.0, "pe": 80.0},
            "23550": {"ce": 20.0, "pe": 140.0},
        },
    )
    _try_open(
        engine,
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        tick=tick,
        ce_path=[120.0],
        pe_path=[80.0],
        bar_i=10,
    )
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is True
    assert not any(s.get("reason") == "NIFTY_WAIT_STRENGTH" for s in engine.skips)


def test_logit_fills_when_dealer_waits_strength() -> None:
    from desk_ml.paper_scalp import _try_open

    weak = {
        "regime": "TREND",
        "direction": "UP",
        "er": 0.10,
        "reason": "weak",
        "last3_impulse": None,
        "last3_reason": "wait_pause_after_impulse",
        "itm_bin": {"side": "CE"},
    }
    engine = BookEngine(nifty_need_strength=True, nifty_allow_sides=("CE", "PE"))
    engine.last_regime["NIFTY"] = weak
    tick = Triple(
        ts=_ts(10),
        idx_close=23367.0,
        ce_close=120.0,
        pe_close=80.0,
        atm_strike=23350.0,
        itm_ce_close=160.0,
        itm_ce_strike=23150.0,
        wing_quotes={
            "23150": {"ce": 160.0, "pe": 20.0},
            "23350": {"ce": 120.0, "pe": 80.0},
            "23550": {"ce": 20.0, "pe": 140.0},
        },
    )
    _try_open(
        engine,
        book_id="MIX-ML-LOGIT",
        underlying="NIFTY",
        side="CE",
        tick=tick,
        ce_path=[120.0],
        pe_path=[80.0],
        bar_i=10,
    )
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is True
    _try_open(
        engine,
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        tick=tick,
        ce_path=[120.0],
        pe_path=[80.0],
        bar_i=10,
    )
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert any(s.get("reason") == "NIFTY_WAIT_STRENGTH" for s in engine.skips)


def test_signal_from_closed_flags_logit_clone() -> None:
    from desk_ml.paper_scalp import signal_from_closed

    closed = [
        {
            "filled": True,
            "book_id": "MIX-DEFAULT-BUY",
            "exit_reason": "CANCEL_STALL",
            "realized_pnl_inr": 100.0,
            "result": "STALL",
        },
        {
            "filled": True,
            "book_id": "MIX-ML-LOGIT",
            "exit_reason": "CANCEL_STALL",
            "realized_pnl_inr": 100.0,
            "result": "STALL",
        },
        {
            "filled": True,
            "book_id": "MIX-ML-LOGIT-XR",
            "exit_reason": "TARGET",
            "target_hit": True,
            "realized_pnl_inr": 800.0,
            "result": "SUCCESS",
        },
    ]
    out = signal_from_closed(closed)
    assert out["desk"] == "SIGNAL"
    assert out["logit_cloned_dealer"] is True
    assert out["best_fill_book"] == "MIX-ML-LOGIT-XR"
    assert out["observe"][0]["n_filled"] == 0
    assert any("cloned dealer" in n for n in out["notes"])
    assert out["promote"] is False


def test_fix_first_drill_progress_json(tmp_path, monkeypatch) -> None:
    from desk_ml.paper_scalp import run_fix_first_drill

    folder = tmp_path / "data" / "recon" / "paper_watch" / "DUAL-TAPE"
    folder.mkdir(parents=True)
    (folder / "2026-09-16.jsonl").write_text("{}\n")
    (folder / "2026-09-17.jsonl").write_text("{}\n")
    (folder / "2026-09-18.jsonl").write_text("{}\n")

    def fake_replay(**kwargs):
        day = kwargs.get("session_ist_date")
        stall = day == "2026-09-18"
        return {
            "ok": True,
            "closed_trades": [
                {
                    "filled": True,
                    "book_id": "MIX-DEFAULT-BUY",
                    "exit_reason": "CANCEL_STALL" if stall else "TARGET",
                    "target_hit": not stall,
                    "result": "TIME" if stall else "SUCCESS",
                    "realized_pnl_inr": 400.0,
                    "underlying": "NIFTY",
                    "side": "CE",
                    "sl_hit": False,
                    "market_kind_open": "TRENDING" if stall else "CHOPPY",
                    "market_kind_close": "CHOPPY" if stall else "CHOPPY",
                    "regime_er": 0.42 if stall else 0.08,
                }
            ],
            "open_trades": [],
            "skip_reason_counts": {"NIFTY_MAX_FILLED": 2} if stall else {},
            "steps": {"NIFTY": {"status": "REPLAY_OK", "n_triples": 40}},
        }

    monkeypatch.setattr("desk_ml.paper_scalp.replay_paper_scalp", fake_replay)
    monkeypatch.setattr(
        "desk_ml.paper_scalp.categorize_tape_hours",
        lambda **kw: {
            "ok": True,
            "day_kind": "SIDEWAYS",
            "day_counts": {"SIDEWAYS": 12},
            "hours": [],
            "n_1m": 12,
        },
    )
    out = run_fix_first_drill(root=tmp_path, persist=True)
    assert [d["ist_date"] for d in out["days"]] == ["2026-09-17", "2026-09-18"]
    assert out["days"][0]["n_target"] == 1
    assert out["days"][1]["n_stall"] == 1
    assert out["days"][1]["n_stall_trending_open"] == 1
    assert out["overlay_recode"] is False
    path = tmp_path / "data" / "recon" / "fix_first_progress.json"
    assert path.is_file()
    dumped = json.loads(path.read_text(encoding="utf-8"))
    dumped["as_of_ist"] = "2026-09-18T16:00:00+05:30"
    path.write_text(json.dumps(dumped) + "\n", encoding="utf-8")
    out2 = run_fix_first_drill(root=tmp_path, persist=True)
    assert out2["history"]
    assert out2["promote"] is False
    assert any("Hour kind" in w for w in out2["watch"])


def test_human_set_levels_does_not_flatten(tmp_path) -> None:
    engine = BookEngine(root=tmp_path)
    engine.equity["MIX-DEFAULT-BUY"] = 10000.0
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="human-levels",
        entry=230.5,
        stop=215.0,
        target=254.0,
        atm_strike=23200.0,
        opened_ts=_ts(0),
        opened_bar=0,
        strike_source="ITM_100",
        limit_price=230.5,
        filled=True,
        last_ltp=234.5,
        index_regime="TREND",
    )
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos
    save_human_override(
        {
            "action": "SET_LEVELS",
            "trade_id": "human-levels",
            "underlying": "NIFTY",
            "side": "CE",
            "target": 270.0,
            "stop": 220.0,
        },
        root=tmp_path,
    )
    tick = Triple(
        ts=_ts(5),
        idx_close=23450.0,
        ce_close=234.5,
        pe_close=80.0,
        atm_strike=23400.0,
        itm_ce_close=234.5,
        itm_ce_strike=23200.0,
        wing_quotes={"23200": {"ce": 234.5, "pe": 40.0}},
    )
    mark_to_market(engine, tick, "NIFTY", 5)
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is True
    kept = engine.opens[("MIX-DEFAULT-BUY", "NIFTY")]
    assert kept.target == 270.0
    assert kept.stop == 220.0


def test_human_naked_exit_does_not_flatten(tmp_path) -> None:
    engine = BookEngine(root=tmp_path)
    engine.equity["MIX-DEFAULT-BUY"] = 10000.0
    pos = OpenPaper(
        book_id="MIX-DEFAULT-BUY",
        underlying="NIFTY",
        side="CE",
        trade_id="human-exit",
        entry=230.5,
        stop=215.0,
        target=254.0,
        atm_strike=23200.0,
        opened_ts=_ts(0),
        opened_bar=0,
        strike_source="ITM_100",
        limit_price=230.5,
        filled=True,
        last_ltp=234.5,
        index_regime="TREND",
    )
    engine.opens[("MIX-DEFAULT-BUY", "NIFTY")] = pos
    path = tmp_path / "data" / "recon" / "human_trade_override.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "ok": True,
                "active": True,
                "action": "EXIT",
                "trade_id": "human-exit",
                "underlying": "NIFTY",
                "side": "CE",
                "orders": "REFUSED",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    tick = Triple(
        ts=_ts(5),
        idx_close=23450.0,
        ce_close=234.5,
        pe_close=80.0,
        atm_strike=23400.0,
        itm_ce_close=234.5,
        itm_ce_strike=23200.0,
        wing_quotes={"23200": {"ce": 234.5, "pe": 40.0}},
    )
    mark_to_market(engine, tick, "NIFTY", 5)
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is True



