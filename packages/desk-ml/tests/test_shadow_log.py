"""Shadow feeds are log-only. Turning them on must not change a fixture replay."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import pytest

from desk_ml.event_parity import fixture_replay_kwargs, load_fixture
from desk_ml.picker import Vote, collect_analyst_votes, picker_majority, shadow_picker_majority
from desk_ml.shadow_flow import near_money_totals, order_flow_score
from desk_ml.shadow_hari import hari_forecast, load_hari_coefficients, log_returns, realized_variance
from desk_ml.shadow_log import build_shadow_row, safe_log_shadow, shadow_logging_enabled
from desk_ml.shadow_volsize import shadow_lots

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "synthetic_session_nifty.json"


def test_hari_expected_move_uses_squared_log_returns():
    closes = [math.exp(i * 0.01) for i in range(6)]
    rets = log_returns(closes)
    assert len(rets) == 5
    assert realized_variance(rets, 5) == pytest.approx(5 * 0.01 ** 2)
    assert realized_variance(rets, 30) is None
    coeffs = {"intercept": 0.0, "rv_5": 1.0, "rv_30": 0.0, "rv_120": 0.0, "rv_prev_day": 0.0, "fitted": False}
    out = hari_forecast(closes, coefficients=coeffs)
    assert out["em30"] == pytest.approx(closes[-1] * math.sqrt(5 * 0.01 ** 2))
    prior = [100.0, 110.0]
    with_prior = hari_forecast(
        closes,
        prior_day_closes=prior,
        coefficients={**coeffs, "rv_5": 0.0, "rv_prev_day": 1.0},
    )
    rv_d = log_returns(prior)[0] ** 2
    assert with_prior["rv_prev_day"] == pytest.approx(rv_d)
    assert with_prior["em30"] == pytest.approx(closes[-1] * math.sqrt(rv_d))


def test_hari_placeholder_coefficients_are_zero():
    coeffs = load_hari_coefficients()
    assert coeffs["fitted"] is False
    assert coeffs["rv_5"] == 0.0 and coeffs["rv_prev_day"] == 0.0
    out = hari_forecast([100.0, 101.0, 102.0, 103.0, 104.0, 105.0], coefficients=coeffs)
    assert out["em30"] == 0.0
    assert out["fitted"] is False


def test_order_flow_score_is_normalised_ce_minus_pe():
    chain = lambda ce_oi, pe_oi, ce_vol, pe_vol: {
        "25000": {"ce_oi": ce_oi, "pe_oi": pe_oi, "ce_volume": ce_vol, "pe_volume": pe_vol},
        "26000": {"ce_oi": 999, "pe_oi": 999, "ce_volume": 999, "pe_volume": 999},
    }
    first = near_money_totals(chain(100, 100, 10, 10), atm=25000, step=50)
    second = near_money_totals(chain(140, 100, 10, 30), atm=25000, step=50)
    assert first is not None and second is not None
    scored = order_flow_score([first, second])
    # dCE oi +40, dPE oi 0, dCE vol 0, dPE vol +20 → num 40 - 0 + 0 - 20 = 20; den 60
    assert scored["score"] == pytest.approx(20 / 60)
    assert -1.0 <= scored["score"] <= 1.0
    assert order_flow_score([first])["score"] is None
    assert near_money_totals({}, atm=25000, step=50) is None


def test_volsize_7b_clips_round_lots():
    assert shadow_lots(27.4) == 25
    assert shadow_lots(137.0) == 5
    assert shadow_lots(50.0) == 14  # round(13.7)
    assert shadow_lots(10.0) == 25  # raw above the cap
    assert shadow_lots(0) is None
    assert shadow_lots(None) is None


def test_shadow_picker_drops_logit_and_xr_without_touching_the_live_vote():
    votes = collect_analyst_votes(
        follows={"side": "CE", "verdict": "BUY_CE_CONFIRM"},
        logit={"side": "PE", "status": "OK", "p": 0.2},
        logit_xr={"side": "PE", "status": "OK"},
        greeks_skip="DATA_INSUFFICIENT",
        ml001_hold=True,
        ml002_hold=True,
        ml1={"side": "CE", "status": "OK"},
        classified={"regime": "SIDEWAYS"},
    )
    assert all(v.source not in {"ML-001", "ML-002", "ML-1"} for v in votes)
    assert any(v.source == "logit" and v.spoken() and v.side == "PE" for v in votes)
    live = picker_majority(votes)
    shadow = shadow_picker_majority(list(votes))
    # follows CE vs logit+xr PE: the live majority follows the logit room. Shadow drops both.
    assert live["action"] == "TICKET" and live["side"] == "PE"
    assert shadow["action"] == "TICKET" and shadow["side"] == "CE"
    # Silent legacy votes, if they were still in the room, would not move the live side.
    padded = list(votes) + [
        Vote("ML-001", None, "SILENT", True, "HOLD"),
        Vote("ML-002", None, "SILENT", True, "HOLD"),
        Vote("ML-1", None, "SILENT", True, "OBSERVE_NO_OWN_SIDE"),
    ]
    again = picker_majority(padded)
    assert (again["action"], again["side"]) == (live["action"], live["side"])


def test_safe_log_swallows_shadow_errors(caplog, tmp_path):
    engine = type("E", (), {"root": tmp_path, "shadow_log": True})()

    def boom(*_a, **_k):
        raise RuntimeError("shadow boom")

    with caplog.at_level(logging.ERROR, logger="desk_ml.shadow_log"):
        import desk_ml.shadow_log as mod

        original = mod.log_decision_shadow
        mod.log_decision_shadow = boom
        try:
            assert safe_log_shadow(engine, underlying="NIFTY", ts=1, votes=[], picker={}) is None
        finally:
            mod.log_decision_shadow = original
    assert "shadow log failed" in caplog.text
    assert not list((tmp_path / "data" / "shadow").glob("*.jsonl"))


def test_build_row_writes_the_schema(tmp_path):
    engine = type("E", (), {"root": tmp_path})()
    votes = [Vote("follows", "CE", "CONFIRM", False, "ok")]
    picker = picker_majority(votes)
    row = build_shadow_row(
        engine,
        underlying="NIFTY",
        ts=1_757_500_000,
        votes=votes,
        picker=picker,
        live_lots=2,
        bars_1m=[{"close": 100.0 + i} for i in range(10)],
        logit={"side": "CE", "p": 0.61},
        wing_quotes={"25000": {"ce_oi": 10, "pe_oi": 12, "ce_volume": 1, "pe_volume": 1}},
        atm=25000.0,
        spot=25010.0,
    )
    assert row["schema"] == "shadow-v1"
    assert row["index"] == "NIFTY"
    assert set(row["live"]) == {"action", "side", "detail", "skip"}
    assert row["agree"] is True
    assert row["logit_p"] == pytest.approx(0.61)
    assert "em30" in row["hari"] and "shadow_lots" in row["volsize_7b"]
    assert row["volsize_7b"]["live_lots"] == 2
    assert shadow_logging_enabled(engine) is True
    engine.shadow_log = False
    assert shadow_logging_enabled(engine) is False


def _replay(monkeypatch, tmp_path, *, shadow: str):
    import desk_ml.paper_scalp as ps

    monkeypatch.setenv("SHADOW_LOG", shadow)
    fx = load_fixture(FIXTURE)
    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})
    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: (int(fx["lot_size"]), "fixture"))
    # write=True: shadow rows are written only by replays that write (write=False writes nothing).
    return ps.replay_paper_scalp(**fixture_replay_kwargs(fx, tmp_path), write=True)


def _fingerprint(board):
    return {
        "closed": board.get("closed_trades") or [],
        "open": board.get("open_trades") or [],
        "skips": board.get("skip_reason_counts") or {},
    }


def test_shadow_on_and_off_keep_the_same_trades(monkeypatch, tmp_path):
    off = _replay(monkeypatch, tmp_path / "off", shadow="0")
    on = _replay(monkeypatch, tmp_path / "on", shadow="1")
    assert _fingerprint(off) == _fingerprint(on)
    assert len([r for r in on["closed_trades"] if r.get("filled")]) > 0
    day = tmp_path / "on" / "data" / "shadow" / "2026-09-10.jsonl"
    rows = [json.loads(line) for line in day.read_text(encoding="utf-8").splitlines() if line]
    assert rows
    assert rows[0]["schema"] == "shadow-v1"
    minutes = [r["minute_ist"] for r in rows]
    assert minutes == sorted(set(minutes))
    assert not (tmp_path / "off" / "data" / "shadow").exists()


def test_shadow_exception_does_not_stop_the_engine(monkeypatch, tmp_path, caplog):
    import desk_ml.shadow_log as mod

    def boom(*_a, **_k):
        raise RuntimeError("shadow boom")

    monkeypatch.setattr(mod, "log_decision_shadow", boom)
    with caplog.at_level(logging.ERROR, logger="desk_ml.shadow_log"):
        blown = _replay(monkeypatch, tmp_path / "boom", shadow="1")
    quiet = _replay(monkeypatch, tmp_path / "quiet", shadow="0")
    assert _fingerprint(blown) == _fingerprint(quiet)
    assert "shadow log failed" in caplog.text
