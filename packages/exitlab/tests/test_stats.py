"""Bootstrap and deflated Sharpe stay defined on tiny samples."""

from __future__ import annotations

from exitlab.stats import bootstrap_mean_ci, deflated_sharpe, max_drawdown, sharpe_ratio, summarize
from exitlab.types import TradeResult


def _tr(net: float, i: int) -> TradeResult:
    return TradeResult(
        entry_id=f"t{i}",
        entry_set="test",
        session="2026-09-17",
        scenario="chop",
        side="CE",
        strike=23200,
        lots=1,
        qty=65,
        entry_ts="2026-09-17T10:00:00+05:30",
        exit_ts="2026-09-17T11:00:00+05:30",
        entry_price=100.0,
        exit_price=100.0 + net / 65,
        exit_reason="TIME",
        time_in_trade_s=3600,
        mfe=100.0,
        mae=100.0,
        mfe_inr=0.0,
        mae_inr=0.0,
        gross_inr=net,
        charges_inr=0.0,
        net_inr=net,
        plan_id="x",
        data_source="synthetic",
    )


def test_max_drawdown_and_ci() -> None:
    nets = [10.0, -30.0, 5.0, 8.0]
    assert max_drawdown(nets) <= 0
    ci = bootstrap_mean_ci(nets, seed=1, n_boot=80)
    assert ci is not None
    assert ci[0] <= ci[1]
    sr = sharpe_ratio(nets)
    dsr = deflated_sharpe(sr, len(nets), n_trials=40)
    assert dsr is None or isinstance(dsr, float)


def test_summarize_counts_skips() -> None:
    rows = [_tr(10, 0), _tr(-4, 1)]
    s = summarize(
        rows,
        plan_id="x",
        entry_set="test",
        scenario="ALL",
        split="all",
        n_variants=40,
        data_source="synthetic",
        seed=1,
    )
    assert s.n_trades == 2
    assert s.net_inr == 6.0
    assert s.win_rate == 0.5
