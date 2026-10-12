"""Stale-price guard: desk prices > 60s behind the wall clock -> no new opens, alert on board and risk."""

from __future__ import annotations

from desk_ml import desk_risk, research_rules as rr

LIVE = {"DESK_RISK_GATE_LIVE": "1"}


def test_staleness_threshold() -> None:
    ok = desk_risk.price_staleness({"NIFTY": 1000.0, "SENSEX": 990.0}, 1050.0)
    assert ok["stale"] is False and ok["alert"] is None and ok["max_lag_s"] == 60.0
    bad = desk_risk.price_staleness({"NIFTY": 1000.0, "SENSEX": 1180.0}, 1000.0 + 198)  # 3.3 min lag
    assert bad["stale"] is True and "NIFTY 198s" in bad["alert"] and "SENSEX" not in bad["alert"]
    assert desk_risk.price_staleness({"NIFTY": None}, 5.0)["stale"] is True


def test_open_block_live_only() -> None:
    assert desk_risk.stale_open_block(1000.0, 1061.0, LIVE) == desk_risk.RISK_STALE_PRICES
    assert desk_risk.stale_open_block(1000.0, 1060.0, LIVE) is None
    assert desk_risk.stale_open_block(1000.0, 5000.0, {}) is None  # replays/goldens unaffected
    assert desk_risk.RISK_STALE_PRICES in desk_risk.RISK_STATUSES


def _row(entry, und="NIFTY"):
    return {"trade_id": entry, "rule_id": rr.R01, "underlying": und, "side": "PE", "atm_strike": 1.0,
            "entry_min": entry, "exit_min": "15:00"}


def test_research_open_on_stale_tape_moved_to_risk_blocked() -> None:
    bars = {"NIFTY": {"14:30": {"ts": 1000}, "14:31": {"ts": 1060}}}
    res = {"open": [_row("14:10"), _row("14:31")], "risk_blocked": []}
    rr.apply_stale_guard(res, bars, now_ts=1060 + 200)
    assert [r["trade_id"] for r in res["open"]] == ["14:10"]
    assert res["risk_blocked"][0]["desk_status"] == desk_risk.RISK_STALE_PRICES
    assert res["price_staleness"]["stale"] is True
    fresh = {"open": [_row("14:31")], "risk_blocked": []}
    rr.apply_stale_guard(fresh, bars, now_ts=1090)
    assert len(fresh["open"]) == 1 and fresh["price_staleness"]["stale"] is False
