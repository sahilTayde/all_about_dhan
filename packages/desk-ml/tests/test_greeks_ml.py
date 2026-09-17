"""MIX-ML-GREEKS rule overlay — Dhan greeks only. NO_PROMOTE."""

from desk_ml.greeks_ml import score_greeks_ticket
from desk_ml.features import Triple
from desk_ml.paper_scalp import BookEngine, LIVE_BOOKS, step_underlying


def test_greeks_ml_hold_missing_and_rich_iv() -> None:
    miss = score_greeks_ticket(side="CE", entry=100.0)
    assert miss["take"] is False
    assert miss["reason"] == "GREEKS_MISSING"
    rich = score_greeks_ticket(side="CE", entry=100.0, delta=0.55, iv=24.0, theta=-3.0)
    assert rich["take"] is False
    assert rich["reason"] == "IV_RICH_ABS"
    late = score_greeks_ticket(
        side="CE",
        entry=100.0,
        delta=0.58,
        iv=12.0,
        theta=-8.0,
        minutes_ist=14 * 60 + 10,
    )
    assert late["take"] is False
    assert late["reason"] == "THETA_LATE_BLEED"
    ok = score_greeks_ticket(side="CE", entry=240.0, delta=0.62, iv=12.0, theta=-8.0, gamma=0.002, minutes_ist=11 * 60)
    assert ok["take"] is True


def test_mix_ml_greeks_skips_without_chain() -> None:
    from datetime import datetime, timezone, timedelta

    IST = timezone(timedelta(hours=5, minutes=30))
    ts = int(datetime(2026, 9, 10, 10, 30, tzinfo=IST).timestamp())
    engine = BookEngine()
    triples = [
        Triple(ts=ts + i * 60, idx_close=23200.0 + i * 8.0, ce_close=80.0, pe_close=70.0)
        for i in range(30)
    ]
    step_underlying(
        engine,
        underlying="NIFTY",
        triples=triples,
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
    assert "MIX-ML-GREEKS" in LIVE_BOOKS
    assert engine.has_open("MIX-ML-GREEKS", "NIFTY") is False
    assert any(s.get("reason") == "GREEKS_MISSING" for s in engine.skips if s.get("book_id") == "MIX-ML-GREEKS")


def test_mix_ml_greeks_opens_when_delta_ok() -> None:
    from datetime import datetime, timezone, timedelta

    IST = timezone(timedelta(hours=5, minutes=30))
    ts = int(datetime(2026, 9, 10, 10, 30, tzinfo=IST).timestamp())
    wings = {
        "23150": {"ce": 140.0, "ce_delta": 0.62, "ce_theta": -7.0, "ce_iv": 12.0, "ce_gamma": 0.002, "ce_vega": 4.1},
            "23250": {"ce": 80.0, "ce_delta": 0.50, "ce_theta": -9.0, "ce_iv": 12.5, "ce_gamma": 0.003, "ce_vega": 3.8},
    }
    engine = BookEngine()
    triples = [
        Triple(
            ts=ts + i * 60,
            idx_close=23250.0 + i * 8.0,
            ce_close=80.0,
            pe_close=70.0,
            atm_strike=23250.0,
            itm_ce_close=140.0,
            itm_ce_strike=23150.0,
            wing_quotes=wings,
        )
        for i in range(30)
    ]
    step_underlying(
        engine,
        underlying="NIFTY",
        triples=triples,
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
    assert engine.has_open("MIX-ML-GREEKS", "NIFTY") is True
    pos = engine.opens[("MIX-ML-GREEKS", "NIFTY")]
    assert pos.delta is not None
    assert abs(float(pos.delta)) >= 0.45
    assert pos.vega is not None
    assert pos.gamma is not None
