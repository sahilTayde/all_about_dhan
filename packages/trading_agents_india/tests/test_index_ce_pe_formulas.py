"""Unit tests for MIX-FORM-* (no cache, no Dhan)."""

from __future__ import annotations

from trading_agents_india.index_ce_pe_formulas import (
    CloseBar,
    align_closes,
    mix_form_beta_resid,
    mix_form_diverge_z,
    mix_form_follow_gap,
    mix_form_straddle_ret,
    ols_beta,
    pearson_corr,
    returns_from_aligned,
    simple_return,
)


def test_simple_return_and_ols_beta() -> None:
    assert simple_return(100.0, 101.0) == 0.01
    assert simple_return(0.0, 1.0) is None
    k = ols_beta([0.01, 0.02, -0.01], [0.02, 0.04, -0.02])
    assert k is not None
    assert abs(k - 2.0) < 1e-9
    resid = mix_form_beta_resid(0.01, 0.025, k)
    assert abs(resid - 0.005) < 1e-12


def test_pearson_perfect_and_thin() -> None:
    assert pearson_corr([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) == 1.0
    assert pearson_corr([1.0], [2.0]) is None


def test_straddle_and_follow_gap() -> None:
    assert mix_form_straddle_ret(0.02, -0.01) == 0.01
    pe_div = mix_form_follow_gap(index_ret=-0.001, ce_ret=-0.01, pe_ret=-0.002)
    assert pe_div["pe_divergence"] is True
    assert pe_div["pe_follow"] is False
    pe_ok = mix_form_follow_gap(index_ret=-0.001, ce_ret=-0.01, pe_ret=0.02)
    assert pe_ok["pe_follow"] is True
    assert pe_ok["pe_divergence"] is False
    ce_div = mix_form_follow_gap(index_ret=0.001, ce_ret=-0.01, pe_ret=-0.01)
    assert ce_div["ce_divergence"] is True
    ce_ok = mix_form_follow_gap(index_ret=0.001, ce_ret=0.02, pe_ret=-0.01)
    assert ce_ok["ce_follow"] is True


def test_diverge_z_constant_is_none() -> None:
    assert mix_form_diverge_z(0.1, [0.1, 0.1, 0.1], window=30) is None
    z = mix_form_diverge_z(3.0, [0.0, 0.1, -0.1, 0.05], window=30)
    assert z is not None
    assert z > 1.0


def test_align_and_returns() -> None:
    idx = [CloseBar(1, 100.0), CloseBar(2, 101.0), CloseBar(3, 99.0)]
    ce = [CloseBar(1, 50.0), CloseBar(2, 52.0), CloseBar(3, 48.0)]
    pe = [CloseBar(1, 40.0), CloseBar(2, 39.0), CloseBar(3, 42.0)]
    aligned = align_closes(idx, ce, pe)
    assert len(aligned) == 3
    rows = returns_from_aligned(aligned)
    assert len(rows) == 2
    assert abs(rows[0]["index_ret"] - 0.01) < 1e-12
    assert rows[0]["ce_ret"] > 0
    assert rows[0]["pe_ret"] < 0
