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
    assert dsr is None or (0.0 <= dsr <= 1.0)


def test_dsr_is_probability_worked_example() -> None:
    """Bailey and Lopez de Prado (2014) eq. 8-11. DSR = Phi((SR - SR*)/se).

    Worked: SR=0.15, n=100, N=20 trials, skew=0, kurtosis=3.
    SR* = se * [(1-euler) invPhi(1-1/N) + euler invPhi(1-1/(N e))].
    """
    import math

    from exitlab.stats import _inv_norm, _norm_cdf

    sr, n, n_trials = 0.15, 100, 20
    got = deflated_sharpe(sr, n, n_trials, skew=0.0, kurt=3.0)
    assert got is not None
    assert 0.0 <= got <= 1.0
    euler = 0.5772156649015329
    e_max_z = (1.0 - euler) * _inv_norm(1.0 - 1.0 / n_trials) + euler * _inv_norm(
        1.0 - 1.0 / (n_trials * math.e)
    )
    se = math.sqrt((1.0 + ((3.0 - 1.0) / 4.0) * sr * sr) / (n - 1))
    sr_star = e_max_z * se
    z = (sr - sr_star) / se
    expected = _norm_cdf(z)
    # Independent Φ via erf
    erf_phi = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    assert abs(expected - erf_phi) < 1e-15
    assert abs(got - erf_phi) < 1e-12
    assert 0.05 < got < 0.95
    huge = deflated_sharpe(10.0, 10, 100)
    tiny = deflated_sharpe(-2.0, 10, 100)
    assert huge is not None and tiny is not None
    assert 0.0 <= tiny <= huge <= 1.0


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
    assert s.low_confidence is True
