"""Parallel paper scalpers: independent books, feasible scalp exits, no win rates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from desk_ml.features import Triple
from desk_ml.paper_scalp import (
    BookEngine,
    LIVE_BOOKS,
    feasibility_long,
    propose_levels,
    replay_paper_scalp,
    step_underlying,
)
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
    assert reasons & {"TIME", "STOP", "TARGET", "FLATTEN_1500"}
    assert all(c["realized_pnl"] is not None for c in closed_tv)
    assert all(c.get("win_rate") is None for c in closed_tv)
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
    assert board["win_rate"] is None
    assert board["independent_books"] is True
    ids = {m["model_id"] for m in board["models"]}
    assert ids == set(LIVE_BOOKS)
    assert board["research_ready_for_programming"] is False
    assert board["execution"] == "refused"
    # ML-1 has no labels on a first pass.
    ml1 = next(m for m in board["models"] if m["model_id"] == "ML-1")
    assert ml1["win_rate"] is None
    lb = board["leaderboard"]
    if lb:
        assert all(row["win_rate"] is None for row in lb)


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
    )
    # Opposite underlyings stay independent even if one overlay HOLDs.
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is True
    assert engine.has_open("MIX-ML-LOGIT", "BANKNIFTY") is True
    assert engine.has_open("ML-001", "NIFTY") is False
    assert engine.has_open("ML-002", "BANKNIFTY") is False
