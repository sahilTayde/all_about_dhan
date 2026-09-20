"""Observer ALLOW/VETO/PASS on a proposed CE/PE. No own side. NO_PROMOTE."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from desk_ml.features import Triple
from desk_ml.observer import (
    ACTION_ALLOW,
    ACTION_PASS,
    ACTION_VETO,
    REASON_ALLOW,
    REASON_ATM,
    REASON_FOLLOW_GAP,
    REASON_INDEX_AGAINST,
    REASON_NO_ITM,
    REASON_STRIKE_ROLL,
    REASON_WING_DEAD,
    apply_observer_to_intents,
    follow_gap_itm_1m,
    observer_review_ticket,
    review_fill_intents,
)
from desk_ml.paper_scalp import BookEngine, FILL_ELIGIBLE_BOOKS, step_underlying

IST = timezone(timedelta(hours=5, minutes=30))


def _bar(*, i: int, idx: float, ce: float, pe: float, kind: str, ce_k: float = 24800.0, pe_k: float = 25200.0) -> Triple:
    ts = int(datetime(2026, 9, 21, 10, 0, tzinfo=IST).timestamp()) + i * 60
    return Triple(
        ts=ts,
        idx_close=idx,
        ce_close=ce,
        pe_close=pe,
        atm_strike=25000.0,
        itm_ce_close=ce,
        itm_pe_close=pe,
        itm_ce_strike=ce_k,
        itm_pe_strike=pe_k,
        premium_kind=kind,
    )


def test_pass_without_side() -> None:
    out = observer_review_ticket(side=None, bar_closed_1m=True)
    assert out["action"] == ACTION_PASS
    assert out["reason"] == "OBSERVER_PASS_NO_SIDE"


def test_pass_atm_day_does_not_veto() -> None:
    a = _bar(i=0, idx=25000, ce=200, pe=180, kind="ATM")
    b = _bar(i=1, idx=25080, ce=199, pe=181, kind="ATM")
    out = observer_review_ticket(side="CE", prev=a, closed=b, bar_closed_1m=True)
    assert out["action"] == ACTION_PASS
    assert out["reason"] == REASON_ATM


def test_pass_missing_itm_kind() -> None:
    a = Triple(ts=1, idx_close=1, ce_close=1, pe_close=1)
    b = Triple(ts=61, idx_close=2, ce_close=1, pe_close=1)
    out = observer_review_ticket(side="CE", prev=a, closed=b, bar_closed_1m=True)
    assert out["action"] == ACTION_PASS
    assert out["reason"] == REASON_NO_ITM


def test_pass_strike_roll() -> None:
    a = _bar(i=0, idx=25000, ce=200, pe=180, kind="ITM", ce_k=24800)
    b = _bar(i=1, idx=25080, ce=190, pe=180, kind="ITM", ce_k=24700)
    out = observer_review_ticket(side="CE", prev=a, closed=b, bar_closed_1m=True)
    assert out["action"] == ACTION_PASS
    assert out["reason"] == REASON_STRIKE_ROLL


def test_follow_gap_itm_1m_ce_dead() -> None:
    a = _bar(i=0, idx=25000, ce=200, pe=180, kind="ITM")
    b = _bar(i=1, idx=25080, ce=198, pe=170, kind="ITM")
    gap = follow_gap_itm_1m(a, b)
    assert gap["ce_gap"] is True
    assert gap["pe_gap"] is False
    assert gap["follow_gap"] is True
    assert gap["rule"] == "FOLLOW_GAP_ITM_1M"


def test_follow_gap_itm_1m_pe_dead() -> None:
    a = _bar(i=0, idx=25000, ce=200, pe=180, kind="ITM")
    b = _bar(i=1, idx=24920, ce=188, pe=178, kind="ITM")
    gap = follow_gap_itm_1m(a, b)
    assert gap["pe_gap"] is True
    assert gap["ce_gap"] is False
    assert gap["follow_gap"] is True
    out = observer_review_ticket(
        side="PE",
        prev=a,
        closed=b,
        classified={"last3_impulse": "DOWN"},
        dealer={"side": "PE", "verdict": "BUY_PE_CONFIRM"},
        bar_closed_1m=True,
    )
    assert out["action"] == ACTION_VETO
    assert out["reason"] == REASON_FOLLOW_GAP


def test_follow_gap_atm_does_not_fire() -> None:
    a = _bar(i=0, idx=25000, ce=200, pe=180, kind="ATM")
    b = _bar(i=1, idx=25080, ce=198, pe=170, kind="ATM")
    gap = follow_gap_itm_1m(a, b)
    assert gap["follow_gap"] is False
    assert gap["pass_reason"] == REASON_ATM


def test_veto_ce_when_itm_ce_dead() -> None:
    a = _bar(i=0, idx=25000, ce=200, pe=180, kind="ITM")
    b = _bar(i=1, idx=25080, ce=198, pe=185, kind="ITM")
    out = observer_review_ticket(
        side="CE",
        prev=a,
        closed=b,
        classified={"last3_impulse": "UP", "index_direction": "UP"},
        dealer={"side": "CE", "verdict": "BUY_CE_CONFIRM"},
        logit={"side": "CE", "status": "OK"},
        bar_closed_1m=True,
    )
    assert out["action"] == ACTION_VETO
    assert out["reason"] == REASON_FOLLOW_GAP
    assert out["ce_gap"] is True
    assert out["claim"]["expected_index"] == "UP"


def test_allow_ce_when_itm_ce_confirms() -> None:
    a = _bar(i=0, idx=25000, ce=200, pe=180, kind="ITM")
    b = _bar(i=1, idx=25080, ce=212, pe=170, kind="ITM")
    out = observer_review_ticket(
        side="CE",
        prev=a,
        closed=b,
        classified={"last3_impulse": "UP"},
        dealer={"side": "CE", "verdict": "BUY_CE_CONFIRM"},
        logit={"side": "CE", "status": "OK"},
        bar_closed_1m=True,
    )
    assert out["action"] == ACTION_ALLOW
    assert out["reason"] == REASON_ALLOW


def test_veto_pe_when_index_up() -> None:
    a = _bar(i=0, idx=25000, ce=200, pe=180, kind="ITM")
    b = _bar(i=1, idx=25080, ce=210, pe=190, kind="ITM")
    out = observer_review_ticket(
        side="PE",
        prev=a,
        closed=b,
        classified={"last3_impulse": "UP"},
        logit={"side": "PE", "status": "OK"},
        bar_closed_1m=True,
    )
    assert out["action"] == ACTION_VETO
    assert out["reason"] == REASON_INDEX_AGAINST


def test_last3_mismatch_does_not_veto_if_1m_confirms() -> None:
    a = _bar(i=0, idx=25000, ce=200, pe=180, kind="ITM")
    b = _bar(i=1, idx=25080, ce=212, pe=170, kind="ITM")
    out = observer_review_ticket(
        side="CE",
        prev=a,
        closed=b,
        classified={"last3_impulse": "DOWN", "index_direction": "DOWN"},
        dealer={"side": "CE", "verdict": "BUY_CE_CONFIRM"},
        bar_closed_1m=True,
    )
    assert out["action"] == ACTION_ALLOW
    assert out["claim"]["self_contradict"] is True


def test_apply_veto_blocks_fill_not_invent_side() -> None:
    intents = {
        "MIX-DEFAULT-BUY": ("CE", None),
        "MIX-ML-LOGIT": ("CE", None),
        "ML-001": (None, "OBSERVE_NO_OWN_SIDE"),
        "MIX-TV-EP-024": (None, "OBSERVE_NO_OWN_FILL"),
    }
    review = {"action": ACTION_VETO, "reason": REASON_FOLLOW_GAP, "side": "CE"}
    out = apply_observer_to_intents(
        intents,
        review,
        fill_books=("MIX-DEFAULT-BUY", "MIX-ML-LOGIT"),
        observe_books=("ML-001", "MIX-TV-EP-024"),
    )
    assert out["MIX-DEFAULT-BUY"] == (None, REASON_FOLLOW_GAP)
    assert out["MIX-ML-LOGIT"] == (None, REASON_FOLLOW_GAP)
    assert out["ML-001"] == (None, REASON_FOLLOW_GAP)


def test_apply_veto_does_not_kill_other_wing() -> None:
    intents = {
        "MIX-DEFAULT-BUY": ("CE", None),
        "MIX-ML-LOGIT": ("PE", None),
    }
    out = apply_observer_to_intents(
        intents,
        {"action": ACTION_VETO, "reason": REASON_FOLLOW_GAP, "side": "CE"},
        fill_books=("MIX-DEFAULT-BUY", "MIX-ML-LOGIT"),
        observe_books=(),
    )
    assert out["MIX-DEFAULT-BUY"] == (None, REASON_FOLLOW_GAP)
    assert out["MIX-ML-LOGIT"] == ("PE", None)


def test_review_fill_intents_per_book_not_first_picker() -> None:
    a = _bar(i=0, idx=25000, ce=200, pe=180, kind="ITM")
    b = _bar(i=1, idx=25080, ce=212, pe=170, kind="ITM")
    intents = {
        "MIX-DEFAULT-BUY": ("CE", None),
        "MIX-ML-LOGIT": ("PE", None),
        "STRAT-001": ("CE", None),
    }
    out, summary, by_book = review_fill_intents(
        intents,
        prev=a,
        closed=b,
        classified={"last3_impulse": "UP"},
        fill_books=("MIX-DEFAULT-BUY", "MIX-ML-LOGIT", "STRAT-001"),
        observe_books=(),
        apply_veto=True,
        bar_closed_1m=True,
    )
    assert out["MIX-DEFAULT-BUY"][0] == "CE"
    assert out["STRAT-001"][0] == "CE"
    assert out["MIX-ML-LOGIT"] == (None, REASON_INDEX_AGAINST)
    assert by_book["MIX-DEFAULT-BUY"]["action"] == ACTION_ALLOW
    assert by_book["STRAT-001"]["action"] == ACTION_ALLOW
    assert by_book["MIX-ML-LOGIT"]["action"] == ACTION_VETO
    assert summary["action"] == ACTION_VETO


def test_apply_pass_leaves_fills() -> None:
    intents = {"MIX-DEFAULT-BUY": ("CE", None), "ML-001": (None, "OBSERVE_NO_OWN_SIDE")}
    out = apply_observer_to_intents(
        intents,
        {"action": ACTION_PASS, "reason": REASON_ATM},
        fill_books=("MIX-DEFAULT-BUY",),
        observe_books=("ML-001",),
    )
    assert out["MIX-DEFAULT-BUY"] == ("CE", None)


def test_step_vetoes_logit_ce_when_itm_dead() -> None:
    bars = []
    idx, ce, pe = 25000.0, 220.0, 160.0
    for i in range(12):
        idx += 12.0
        ce -= 1.5
        pe += 0.4
        bars.append(_bar(i=i, idx=idx, ce=ce, pe=pe, kind="ITM"))
    engine = BookEngine(
        skip_new_when_sideways=False,
        nifty_need_strength=False,
        sod_one_ticket=False,
        picker_majority=False,
    )
    engine.capital_by_book = {b: 150000.0 for b in FILL_ELIGIBLE_BOOKS}
    for i in range(1, 11):
        step_underlying(
            engine,
            underlying="NIFTY",
            triples=bars,
            i=i,
            ml001_hold=False,
            ml002_hold=False,
            follow_gap=False,
            logit={"side": "CE", "status": "OK"},
            logit_xr={"side": "CE", "status": "OK"},
            ml1={"status": "OK", "take": True},
            tv_side="CE",
            deny_model_signals=True,
        )
    review = engine.observer_review.get("NIFTY") or {}
    by_book = engine.observer_by_book.get("NIFTY") or {}
    assert (by_book.get("MIX-ML-LOGIT") or {}).get("action") == ACTION_VETO
    assert review.get("action") == ACTION_VETO
    assert review.get("reason") == REASON_FOLLOW_GAP
    assert review.get("follow_gap") is True
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is False
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
    assert any(s.get("reason") == REASON_FOLLOW_GAP for s in engine.skips)


def test_step_atm_tape_does_not_observer_veto() -> None:
    bars = []
    idx, ce, pe = 25000.0, 120.0, 110.0
    for i in range(12):
        idx += 12.0
        ce += 1.8
        pe -= 1.2
        bars.append(_bar(i=i, idx=idx, ce=ce, pe=pe, kind="ATM"))
    engine = BookEngine(skip_new_when_sideways=False, nifty_need_strength=False)
    engine.capital_by_book = {b: 150000.0 for b in FILL_ELIGIBLE_BOOKS}
    for i in range(1, 11):
        step_underlying(
            engine,
            underlying="NIFTY",
            triples=bars,
            i=i,
            ml001_hold=False,
            ml002_hold=False,
            follow_gap=False,
            logit={"side": "CE", "status": "OK"},
            logit_xr={"side": None, "status": "SKIP"},
            ml1={"status": "DATA_INSUFFICIENT"},
            tv_side="CE",
            deny_model_signals=True,
        )
    review = engine.observer_review.get("NIFTY") or {}
    assert review.get("action") == ACTION_PASS
    assert review.get("reason") == REASON_ATM
    assert not any(str(s.get("reason") or "").startswith("OBSERVER_VETO") for s in engine.skips)
    assert engine.has_open("MIX-DEFAULT-BUY", "NIFTY") is False
