"""Live optionchain parse — documented data.oc / last_price only."""

from __future__ import annotations

from trading_agents_india.fixtures import DRY_RUN_CHAIN_GAP
from trading_agents_india.hooks.chain import _metrics_from_dhan_payload
from trading_agents_india.hooks.premium import resolve_premium_lean
from trading_agents_india.pipeline import drop_stale_dry_run_chain_gap


def _oc_payload(*, ce_buildup: bool) -> dict:
    # ATM 25000. CE adding more OI than PE when ce_buildup.
    ce_prev, pe_prev = (100, 100)
    ce_now = 400 if ce_buildup else 110
    pe_now = 110 if ce_buildup else 400
    oc = {}
    prices = {24900: (140.0, 40.0), 25000: (80.0, 70.0), 25100: (40.0, 130.0)}
    for k in (24900, 25000, 25100):
        ce_px, pe_px = prices[k]
        oc[str(k)] = {
            "ce": {
                "oi": ce_now,
                "previous_oi": ce_prev,
                "volume": 10,
                "last_price": ce_px,
                "implied_volatility": 18.0,
                "greeks": {
                    "delta": {24900: 0.62, 25000: 0.50, 25100: 0.38}[k],
                    "theta": -8.0,
                    "gamma": 0.002,
                    "vega": 4.0,
                },
            },
            "pe": {
                "oi": pe_now,
                "previous_oi": pe_prev,
                "volume": 10,
                "last_price": pe_px,
                "implied_volatility": 19.0,
                "greeks": {
                    "delta": {24900: -0.38, 25000: -0.50, 25100: -0.62}[k],
                    "theta": -7.5,
                    "gamma": 0.002,
                    "vega": 4.0,
                },
            },
        }
    return {"data": {"last_price": 25010, "oc": oc}}


def test_metrics_parse_ce_buildup() -> None:
    lean, gaps, meta = _metrics_from_dhan_payload(
        _oc_payload(ce_buildup=True), underlying="NIFTY", expiry="2026-09-08"
    )
    assert lean == "CE"
    assert meta["strike_count"] == 3
    assert meta["spot"] == 25010
    assert meta["atm_ce_ltp"] == 80.0
    assert meta["itm_ce_strike"] == 24900.0
    assert meta["itm_ce_ltp"] == 140.0
    assert meta["itm_pe_strike"] == 25100.0
    assert meta["itm_pe_ltp"] == 130.0
    assert meta["atm_ce_delta"] == 0.50
    assert meta["itm_ce_delta"] == 0.62
    assert meta["atm_ce_iv"] == 18.0
    assert meta["atm_ce_theta"] == -8.0
    assert meta["atm_ce_vega"] == 4.0
    assert meta["itm_ce_vega"] == 4.0
    assert meta["itm_ce_gamma"] == 0.002
    packed = (meta.get("wing_quotes") or {}).get("24900") or {}
    assert packed["ce_vega"] == 4.0
    assert packed["ce_delta"] == 0.62
    assert packed["ce_oi"] == 400
    assert meta["pcr_oi"] is not None
    assert not any("lacks parseable lean" in g for g in gaps)


def test_drop_stale_dry_run_gap_only_when_live() -> None:
    analog = "DATA_INSUFFICIENT: EVENT_MEMORY analog store empty"
    gaps = [DRY_RUN_CHAIN_GAP, analog]
    live = drop_stale_dry_run_chain_gap(gaps, chain_source="dhan_live")
    assert DRY_RUN_CHAIN_GAP not in live
    assert analog in live
    fx = drop_stale_dry_run_chain_gap(gaps, chain_source="fixture")
    assert DRY_RUN_CHAIN_GAP in fx


def test_premium_levels_from_chain_watch() -> None:
    result = resolve_premium_lean(
        "NIFTY",
        prefer_live=True,
        chain_lean="CE",
        chain_watch={"atm_ce_ltp": 80.0, "atm_pe_ltp": 70.0, "atm_strike": 25000},
    )
    assert result.source == "optionchain_atm"
    assert result.option_ltp == 80.0
    assert result.entry == 80.0
    assert result.stop == 60.0
    assert result.target == 100.0
