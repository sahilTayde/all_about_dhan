"""WAITING MIX-LEAN evaluators — gather INDEX 1m + ATM/PCR; no promote."""

from __future__ import annotations

from trading_agents_india.lean_mix import (
    pick_customer_lean,
    score_dual_index_master,
    score_impulse_1m,
    score_lean_spot_atm,
    score_pcr_extreme_hold,
    score_sell_credit_park,
)
from trading_agents_india.paper_evaluators import evaluate_candidate
from trading_agents_india.schemas import PaperTicket


def _ticket(**kwargs) -> PaperTicket:
    base = dict(
        underlying="NIFTY",
        lean="HOLD",
        stage="WATCH",
        reasons=["test"],
        risk_veto=False,
        vetoes=[],
        session_kind="NORMAL",
        premium_lean={},
    )
    base.update(kwargs)
    return PaperTicket(**base)  # type: ignore[arg-type]


def _bars(*, n: int = 12, start: float = 24000.0, step: float = 8.0):
    from backtest_engine.indicators import Bar

    out = []
    for i in range(n):
        c = start + i * step
        out.append(Bar(ts=i, open=c - 1, high=c + 1, low=c - 2, close=c, volume=1))
    return out


def test_spot_atm_early_when_index_last_and_atm_ltp() -> None:
    ticket = _ticket(
        premium_lean={
            "spot": 24800.0,
            "chain_lean": "CE",
            "source": "optionchain_atm",
            "option_ltp": 80.0,
            "pcr_oi": 0.95,
        }
    )
    hit = score_lean_spot_atm(ticket, bars=_bars())
    assert hit.lean == "BUY_CE"
    assert hit.stage == "EARLY"
    assert hit.entry == 80.0
    assert hit.stop == 60.0
    assert hit.target == 100.0
    result = evaluate_candidate("MIX-LEAN-SPOT-ATM", ticket, bars=_bars())
    assert result.outcome == "BUY_CE"
    assert result.provenance_extra.get("customer_default") is False
    assert result.provenance_extra.get("NO_PROMOTE") is True


def test_spot_atm_empty_sl_tp_without_ltp() -> None:
    ticket = _ticket(
        premium_lean={
            "spot": 24800.0,
            "chain_lean": "PE",
            "source": "optionchain_atm",
        }
    )
    hit = score_lean_spot_atm(ticket, bars=_bars())
    assert hit.lean == "BUY_PE"
    assert hit.stage == "WATCH"
    assert hit.entry is None
    assert hit.stop is None
    assert hit.target is None


def test_impulse_1m_ce_from_lookback() -> None:
    bars = _bars(n=8, start=24000.0, step=10.0)
    ticket = _ticket(
        premium_lean={
            "source": "optionchain_atm",
            "option_ltp": 50.0,
            "chain_lean": "NEUTRAL",
        }
    )
    hit = score_impulse_1m(ticket, bars=bars)
    assert hit.lean == "BUY_CE"
    assert hit.entry == 50.0


def test_pcr_hold_without_price() -> None:
    ticket = _ticket(premium_lean={"pcr_oi": 1.4, "chain_lean": "NEUTRAL"})
    hit = score_pcr_extreme_hold(ticket, bars=None)
    assert hit.outcome == "HOLD"
    assert hit.lean == "HOLD"
    picked = pick_customer_lean(ticket, bars=None)
    assert picked.mix_id == "MIX-PCR-EXTREME-HOLD"
    assert picked.lean == "HOLD"


def test_pcr_idle_when_priced_wall() -> None:
    ticket = _ticket(
        premium_lean={
            "pcr_oi": 0.9,
            "spot": 24800.0,
            "chain_lean": "CE",
            "source": "optionchain_atm",
            "option_ltp": 70.0,
        }
    )
    hit = score_pcr_extreme_hold(ticket, bars=_bars())
    assert hit.outcome == "ALLOW"
    picked = pick_customer_lean(ticket, bars=_bars())
    assert picked.mix_id == "MIX-LEAN-SPOT-ATM"
    assert picked.lean == "BUY_CE"


def test_sell_credit_never_buys() -> None:
    hit = score_sell_credit_park(_ticket(lean="BUY_CE"))
    assert hit.lean == "HOLD"
    assert hit.outcome == "PARKED"
    result = evaluate_candidate("STRAT-013", _ticket(lean="BUY_CE"))
    assert result.outcome == "PARKED"
    assert result.final_lean == "HOLD"


def test_index_proxy_003_006_watch_not_confirmed() -> None:
    bars = _bars(n=90, start=24000.0, step=2.0)
    ticket = _ticket()
    r3 = evaluate_candidate("MIX-003-INDEX-PROXY", ticket, bars=bars)
    r6 = evaluate_candidate("MIX-006-INDEX-PROXY", ticket, bars=bars)
    assert r3.available is True
    assert r6.available is True
    assert r3.provenance_extra.get("proxy_label") == "INDEX_RESAMPLE_NE_FUTIDX"
    assert r6.provenance_extra.get("proxy_label") == "INDEX_RESAMPLE_NE_OPTIDX"
    assert r3.provenance_extra.get("mix_stage") == "WATCH"
    assert r6.provenance_extra.get("mix_stage") == "WATCH"


def test_default_buy_not_rewritten_when_lean_mix_cited() -> None:
    ticket = _ticket(
        lean="BUY_CE",
        lean_mix_cited="MIX-LEAN-SPOT-ATM",
        default_mix_cited="MIX-DEFAULT-BUY",
    )
    result = evaluate_candidate("MIX-DEFAULT-BUY", ticket)
    assert result.final_lean == "HOLD"
    assert result.outcome == "WATCH"
    assert "not rewritten" in str(result.provenance_extra.get("note"))


def test_dual_index_master_sensex_waits_for_premium_ohlc() -> None:
    ticket = _ticket(
        underlying="SENSEX",
        premium_lean={
            "source": "optionchain_atm",
            "option_ltp": 100.0,
        },
    )
    hit = score_dual_index_master(ticket, bars=_bars(n=30, start=74000.0, step=10.0))
    assert hit.lean == "HOLD"
    assert hit.outcome == "DATA_INSUFFICIENT"
    assert hit.provenance["NO_PROMOTE"] is True
    assert any("CALL premium OHLC" in gap for gap in hit.data_gaps)
    result = evaluate_candidate(
        "MIX-DUAL-INDEX-MASTER",
        ticket,
        bars=_bars(n=30, start=74000.0, step=10.0),
    )
    assert result.final_lean == "HOLD"
    assert result.provenance_extra.get("mix_stage") == "WATCH"


def test_dual_index_master_nifty_failed_arm_parked() -> None:
    hit = score_dual_index_master(_ticket(underlying="NIFTY"), bars=_bars(n=30))
    assert hit.lean == "HOLD"
    assert hit.outcome == "PARKED"
    assert hit.provenance["latest_shadow_oos_expectancy"] < 0
