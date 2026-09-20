"""SOD rooms: picker majority → observer → one desk ticket. PAPER. NO_PROMOTE."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from desk_ml.features import Triple
from desk_ml.llm_review import (
    INSTR_WAIT,
    JOB_ALLOW,
    compact_counsel,
    maybe_llm_review,
    mock_counsel,
)
from desk_ml.observer import ACTION_ALLOW, ACTION_PASS, ACTION_VETO, REASON_FOLLOW_GAP
from desk_ml.paper_scalp import (
    FILL_ELIGIBLE_BOOKS,
    LIVE_BOOKS,
    BookEngine,
    bin_both_wings_packet,
    step_underlying,
)
from desk_ml.picker import (
    HOLD_CLOSE,
    SOD_ONE_OPEN,
    SOD_PRODUCT_BOOK,
    Vote,
    collect_analyst_votes,
    picker_majority,
    strat_votes,
    track_model_signals,
)

IST = timezone(timedelta(hours=5, minutes=30))


def _bar(*, i: int, idx: float, ce: float, pe: float, kind: str = "ITM", vol: float = 1000.0) -> Triple:
    ts = int(datetime(2026, 9, 21, 10, 0, tzinfo=IST).timestamp()) + i * 60
    return Triple(
        ts=ts,
        idx_close=idx,
        ce_close=ce,
        pe_close=pe,
        atm_strike=25000.0,
        itm_ce_close=ce,
        itm_pe_close=pe,
        itm_ce_strike=24800.0,
        itm_pe_strike=25200.0,
        premium_kind=kind,
        idx_volume=vol,
        wing_quotes={
            24800.0: {"ce_volume": vol, "pe_volume": vol * 0.8},
            25200.0: {"ce_volume": vol * 0.8, "pe_volume": vol},
        },
    )


def _engine(**kw: object) -> BookEngine:
    engine = BookEngine(
        skip_new_when_sideways=False,
        nifty_need_strength=False,
        skip_sensex=True,
        skip_banknifty=True,
        **kw,  # type: ignore[arg-type]
    )
    engine.capital_by_book = {b: 150000.0 for b in LIVE_BOOKS}
    return engine


def _step(engine: BookEngine, bars: list[Triple], i: int, **kw: object) -> None:
    step_underlying(
        engine,
        underlying="NIFTY",
        triples=bars,
        i=i,
        ml001_hold=False,
        ml002_hold=False,
        follow_gap=False,
        logit=kw.get("logit") or {"side": "CE", "status": "OK"},  # type: ignore[arg-type]
        logit_xr=kw.get("logit_xr") or {"side": "CE", "status": "OK"},  # type: ignore[arg-type]
        ml1={"status": "DATA_INSUFFICIENT"},
        tv_side="CE",
        deny_model_signals=True,
    )


def test_picker_majority_same_class() -> None:
    votes = [
        Vote("follows", "CE", "CONFIRM", False),
        Vote("logit", "CE", "CONFIRM", False),
        Vote("xr", "CE", "CONFIRM", False),
    ]
    out = picker_majority(votes)
    assert out["action"] == "TICKET"
    assert out["side"] == "CE"
    assert out["llm"] is False


def test_picker_hold_8_7() -> None:
    votes = [Vote(f"a{i}", "CE", "CONFIRM", False) for i in range(8)]
    votes += [Vote(f"b{i}", "PE", "CONFIRM", False) for i in range(7)]
    out = picker_majority(votes)
    assert out["action"] == "HOLD"
    assert out["skip"] == HOLD_CLOSE
    assert out["detail"] == "HOLD_CLOSE_8_7"


def test_picker_soup_and_silent_does_not_vote() -> None:
    votes = collect_analyst_votes(
        follows={"side": "CE", "verdict": "BUY_CE_CONFIRM"},
        logit={"side": "PE", "status": "OK"},
        logit_xr={"side": None, "status": "DATA_INSUFFICIENT"},
        greeks_skip="DATA_INSUFFICIENT",
        classified={"regime": "SIDEWAYS"},
    )
    spoken = [v for v in votes if v.spoken()]
    assert all(v.source != "dealer" for v in votes)
    assert any(v.source == "follows" and v.side == "CE" for v in spoken)
    assert all(v.source != "ML-001" or v.silent for v in votes)
    assert any(v.source.startswith("STRAT-") and v.silent for v in votes)
    out = picker_majority(votes)
    assert out["action"] == "HOLD"
    assert out["n_spoken"] == len(spoken) == 2


def test_picker_index_against_hold() -> None:
    votes = [Vote("follows", "PE", "CONFIRM", False), Vote("logit", "PE", "CONFIRM", False)]
    out = picker_majority(votes, classified={"direction": "UP", "index_direction": "UP"})
    assert out["action"] == "HOLD"
    assert out["detail"] == "HOLD_INDEX_AGAINST"


def test_strat_keep_all_fourteen_silent_or_vote() -> None:
    rows = strat_votes(classified={"regime": "UNKNOWN"})
    assert [v.source for v in rows] == [f"STRAT-{i:03d}" for i in range(1, 15)]
    assert all(v.silent for v in rows)


def test_observer_after_picker_veto_not_fill() -> None:
    bars = []
    idx, ce, pe = 25000.0, 220.0, 160.0
    for i in range(14):
        idx += 12.0
        ce -= 1.5
        pe += 0.4
        bars.append(_bar(i=i, idx=idx, ce=ce, pe=pe))
    engine = _engine(sod_one_ticket=True, picker_majority=True, observer_veto_fills=True)
    for i in range(1, 13):
        _step(engine, bars, i)
    assert engine.has_open(SOD_PRODUCT_BOOK, "NIFTY") is False
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is False
    step = engine.last_step
    assert [v["source"] for v in step["analyst_votes"] if str(v["source"]).startswith("STRAT-")]
    assert step["picker"]["action"] in {"HOLD", "TICKET"}
    assert step["observer"]["action"] in {ACTION_VETO, ACTION_PASS, ACTION_ALLOW, "PASS", "VETO", "ALLOW"}
    assert any(r["source"] == "logit" for r in step["model_signals"])
    if step["observer"]["action"] == ACTION_ALLOW:
        assert step["llm_review"] and step["llm_review"]["job"] == JOB_ALLOW
        assert step["llm_review"]["blocked_open"] is False
    else:
        assert step["llm_review"] is None
    if step["picker"]["action"] == "TICKET":
        assert step["observer"]["action"] == ACTION_VETO
        assert step["observer"]["reason"] == REASON_FOLLOW_GAP


def test_one_open_blocks_second_fill() -> None:
    bars = []
    idx, ce, pe = 25000.0, 120.0, 180.0
    for i in range(16):
        idx += 8.0
        ce += 2.2
        pe -= 1.1
        bars.append(_bar(i=i, idx=idx, ce=ce, pe=pe, vol=2000 + i * 50))
    engine = _engine(sod_one_ticket=True, picker_majority=True, nifty_max_filled_per_book=4)
    for i in range(1, 15):
        _step(engine, bars, i)
    n_prod = sum(1 for k in engine.opens if k[0] == SOD_PRODUCT_BOOK)
    n_lab = sum(1 for k in engine.opens if k[0] in FILL_ELIGIBLE_BOOKS and k[0] != SOD_PRODUCT_BOOK)
    assert n_lab == 0
    assert n_prod <= 1
    assert any(s.get("reason") == SOD_ONE_OPEN for s in engine.skips) or n_prod == 1
    step = engine.last_step
    if step["observer"]["action"] == ACTION_ALLOW:
        assert step["llm_review"]["job"] == JOB_ALLOW
        assert step["llm_review"]["blocked_open"] is False
    assert step["desk"]["sod_one_ticket"] is True
    assert engine.signal_log


def test_bin_both_wings_oi_data_insufficient() -> None:
    pkt = bin_both_wings_packet(
        {
            "ce": {"strike": 24800, "px": 120, "volume": 10, "oi": None},
            "pe": {"strike": 25200, "px": 90, "volume": 12, "oi": None},
            "ce_votes": ["CE_PREMIUM_UP"],
            "pe_votes": ["PE_PREMIUM_DOWN"],
            "side": "CE",
            "missing": ["ce_oi", "pe_oi"],
        }
    )
    assert pkt["ce"]["oi"] == "DATA_INSUFFICIENT"
    assert pkt["pe"]["oi"] == "DATA_INSUFFICIENT"
    assert pkt["ce"]["trend_votes"]
    assert pkt["pe"]["trend_votes"]


def test_llm_on_allow_nonblocking_and_fail_soft() -> None:
    mock = mock_counsel("risk-review", {"side": "CE"})
    assert mock["mock"] is True
    assert mock["blocked_open"] is False
    assert mock["instruction"] == INSTR_WAIT
    allow = maybe_llm_review(trigger="ALLOW", compact={"side": "CE"}, observer_action="ALLOW")
    assert allow is not None
    assert allow["job"] == JOB_ALLOW
    assert allow["blocked_open"] is False
    assert allow["instruction"] == INSTR_WAIT
    assert maybe_llm_review(trigger="STOP", compact={"side": "CE"}, opened_this_tick=True) is None
    called = {"n": 0}

    def boom(**_kw: object) -> dict:
        called["n"] += 1
        raise RuntimeError("no network")

    out = compact_counsel("exit-review", {"side": "PE"}, force_mock=False, complete_fn=boom)
    assert out["instruction"] == INSTR_WAIT
    assert out["blocked_open"] is False
    assert "sk-" not in str(out)
    assert "GEMINI_API_KEY" not in str(out)

    with patch.dict("os.environ", {"GEMINI_API_KEY": "", "OPENAI_API_KEY": ""}, clear=False):
        env_out = compact_counsel("partial-book-review", {"side": "CE"}, force_mock=False)
    assert env_out["mock"] is True
    assert env_out["blocked_open"] is False


def test_trace_rooms_on_step() -> None:
    bars = [_bar(i=i, idx=25000 + i, ce=100 + i, pe=100 - i, kind="ATM") for i in range(8)]
    engine = _engine(sod_one_ticket=True, picker_majority=True)
    _step(engine, bars, 2)
    step = engine.last_step
    for key in ("follows", "analyst_votes", "picker", "observer", "desk", "overlay_to_boss", "bin_both_wings"):
        assert key in step
    assert step["trace"] == ["follows", "picker", "observer", "desk"]
    assert step["desk"]["kind"] == "DESK"
    assert "model_signals" in step
    if step["observer"]["action"] == ACTION_ALLOW:
        assert step["llm_review"]["job"] == JOB_ALLOW
    else:
        assert step["llm_review"] is None
    assert step["desk"]["sod_one_ticket"] is True
    assert engine.has_open(SOD_PRODUCT_BOOK, "NIFTY") is False


def test_sod_itm_tape_can_open_after_allow() -> None:
    bars = []
    idx, ce, pe = 25000.0, 120.0, 180.0
    for i in range(16):
        idx += 8.0
        ce += 2.2
        pe -= 1.1
        bars.append(_bar(i=i, idx=idx, ce=ce, pe=pe, vol=2000 + i * 50))
    engine = _engine()
    for i in range(1, 15):
        _step(engine, bars, i)
    step = engine.last_step
    assert "follows" in step
    if engine.has_open(SOD_PRODUCT_BOOK, "NIFTY"):
        pos = engine.opens[(SOD_PRODUCT_BOOK, "NIFTY")]
        assert pos.quote_src != "ATM"
        assert step["observer"]["action"] == ACTION_ALLOW
    else:
        assert step["picker"]["action"] in {"HOLD", "TICKET"}
        assert step["observer"]["action"] in {ACTION_VETO, ACTION_PASS, ACTION_ALLOW}


def test_sod_defaults_on() -> None:
    from desk_ml.paper_scalp import DEFAULT_PAPER_PARAMS, BookEngine

    assert DEFAULT_PAPER_PARAMS["sod_one_ticket"] is True
    assert DEFAULT_PAPER_PARAMS["picker_majority"] is True
    assert BookEngine().sod_one_ticket is True
    assert BookEngine().picker_majority is True


def test_track_model_signals_dissent_when_picker_hold() -> None:
    votes = collect_analyst_votes(
        follows={"side": "CE", "verdict": "BUY_CE_CONFIRM"},
        logit={"side": "PE", "status": "OK"},
        logit_xr={"side": "PE", "status": "OK"},
        greeks_side="CE",
    )
    picker = picker_majority(votes)
    rows = track_model_signals(votes, picker, {"action": ACTION_VETO})
    by_src = {r["source"]: r for r in rows}
    assert by_src["logit"]["side"] == "PE"
    assert by_src["xr"]["side"] == "PE"
    assert by_src["greeks"]["side"] == "CE"
    if picker["action"] == "HOLD":
        assert by_src["logit"]["vs_picker"] == "SPOKEN_PICKER_HOLD"
        assert by_src["xr"]["vs_picker"] == "SPOKEN_PICKER_HOLD"
    assert by_src["logit"]["observer_action"] == ACTION_VETO


def test_thin_tape_hold_majority() -> None:
    votes = collect_analyst_votes(
        follows={"side": None, "verdict": "DATA_INSUFFICIENT"},
        logit={"side": None, "status": "DATA_INSUFFICIENT"},
        logit_xr={"side": None, "status": "DATA_INSUFFICIENT"},
        greeks_skip="DATA_INSUFFICIENT",
        classified={},
    )
    out = picker_majority(votes)
    assert out["action"] == "HOLD"
    assert out["n_spoken"] == 0


def test_greeks_vote_without_fill_intents() -> None:
    from desk_ml.picker import greeks_vote_intent

    side, skip = greeks_vote_intent(dealer_confirm="CE", logit={"side": "CE", "status": "OK"})
    assert side is None
    assert skip == "GREEKS_NO_CLONE"
    side, skip = greeks_vote_intent(dealer_confirm="PE", logit={"side": None})
    assert side == "PE"
    assert skip is None
    votes = collect_analyst_votes(
        follows={"side": "PE", "verdict": "BUY_PE_CONFIRM"},
        logit={"side": None, "status": "DATA_INSUFFICIENT"},
        logit_xr={"side": None, "status": "DATA_INSUFFICIENT"},
        greeks_side=side,
        greeks_skip=skip,
        tv_side="CE",
        classified={"regime": "TREND", "direction": "UP"},
    )
    by = {v.source: v for v in votes}
    assert by["greeks"].spoken() and by["greeks"].side == "PE"
    assert by["MIX-TV-EP-024"].spoken() and by["MIX-TV-EP-024"].side == "CE"
    assert by["STRAT-003"].spoken() and by["STRAT-003"].side == "CE"
    assert by["greeks"].packet()["reason"] == "GREEKS"


def test_sod_skips_fill_router_and_lab_opens() -> None:
    bars = []
    idx, ce, pe = 25000.0, 120.0, 180.0
    for i in range(16):
        idx += 8.0
        ce += 2.2
        pe -= 1.1
        bars.append(_bar(i=i, idx=idx, ce=ce, pe=pe, vol=2000 + i * 50))
    engine = _engine(sod_one_ticket=True, picker_majority=True)
    for i in range(1, 15):
        _step(engine, bars, i)
    step = engine.last_step
    assert step["fill_router"] == "sod_desk"
    assert step["independent"] is False
    assert step["desk"]["fill_router"] == "sod_desk"
    assert engine.has_open("MIX-ML-LOGIT", "NIFTY") is False
    assert engine.has_open("MIX-ML-LOGIT-XR", "NIFTY") is False
    assert engine.has_open("MIX-ML-GREEKS", "NIFTY") is False
    assert engine.has_open("MIX-TV-EP-024", "NIFTY") is False
    sources = {v["source"] for v in step["analyst_votes"]}
    assert "follows" in sources and "logit" in sources and "greeks" in sources
    assert "STRAT-003" in sources and "MIX-TV-EP-024" in sources
    assert any(r.get("reason") for r in step["analyst_votes"])
    sig_src = {r["source"] for r in step["model_signals"]}
    assert "logit" in sig_src
    assert "MIX-TV-EP-024" in sig_src


def test_spoken_votes_logged_when_picker_hold_and_observer_veto() -> None:
    votes = collect_analyst_votes(
        follows={"side": "CE", "verdict": "BUY_CE_CONFIRM"},
        logit={"side": "PE", "status": "OK"},
        logit_xr={"side": "PE", "status": "OK"},
        greeks_side="CE",
        tv_side="PE",
        classified={"regime": "TREND", "direction": "DOWN"},
    )
    picker = picker_majority(votes, classified={"direction": "UP", "index_direction": "UP"})
    assert picker["action"] == "HOLD"
    rows = track_model_signals(
        votes, picker, {"action": ACTION_VETO}, desk_opened=False, desk_side=None
    )
    by_src = {r["source"]: r for r in rows}
    assert by_src["logit"]["vs_picker"] == "SPOKEN_PICKER_HOLD"
    assert by_src["xr"]["ignored_by_boss"] is True
    assert by_src["MIX-TV-EP-024"]["side"] == "PE"
    assert "STRAT-003" in by_src
    assert by_src["STRAT-003"]["vs_picker"] in {"SPOKEN_PICKER_HOLD", "SILENT", "DISSENT", "MATCH"}


def test_sod_off_still_uses_resolve_fill_intents() -> None:
    bars = [_bar(i=i, idx=25000 + i * 8, ce=120 + i, pe=180 - i, vol=2000) for i in range(8)]
    engine = _engine(sod_one_ticket=False, picker_majority=False)
    _step(engine, bars, 4)
    step = engine.last_step
    assert step["fill_router"] == "resolve_fill_intents"
    assert step["independent"] is True
