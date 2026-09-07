"""Tests for CF overnight paper registry + structure detector. PAPER only."""

from __future__ import annotations

from backtest_engine.cf_overnight_catalog import SKIP_MIXES, build_catalog
from backtest_engine.cf_paper_registry import (
    clear_plugins,
    detect_cf_signal,
    list_plugins,
    registry_meta,
)
from backtest_engine.cf_structure_paper import (
    StructurePaperCell,
    clear_structure_cache,
    detect_structure_signal,
    load_structure_eligible_cells,
)
from backtest_engine.indicators import Bar
from backtest_engine.levels import bind_option_premium_levels


def _bars(n: int = 120) -> list[Bar]:
    base = 1704155400
    return [
        Bar(
            ts=base + i * 60,
            open=24000.0 + (i % 7),
            high=24020.0 + (i % 7),
            low=23980.0 + (i % 7),
            close=24000.0 + (i % 7),
            volume=1.0,
        )
        for i in range(n)
    ]


def test_catalog_builds_and_skips_named():
    arms = build_catalog()
    assert len(arms) >= 20
    mix_ids = {a.mix_id for a in arms}
    assert "MIX-CF-MARCO-LIQ-TRAP" in mix_ids
    assert "MIX-CF-OKALA-IN-LEVEL" not in mix_ids  # Okala has own runner
    skip_ids = {s["mix_id"] for s in SKIP_MIXES}
    assert "MIX-CF-USMAN-0DTE-GAMMA" in skip_ids
    assert not (mix_ids & skip_ids)


def test_registry_includes_okala_and_structure():
    clear_plugins()
    plugs = list_plugins()
    ids = [p.plugin_id for p in plugs]
    assert "okala_in" in ids
    assert "cf_structure_in" in ids
    meta = registry_meta()
    assert meta["NO_PROMOTE"] is True
    assert len(meta["plugins"]) >= 2


def test_detect_cf_signal_premium_shape_when_forced(monkeypatch):
    """Registry returns Okala-shaped premium when a plugin hits."""
    clear_plugins()
    from backtest_engine import cf_paper_registry as reg

    def fake_detect(underlying, bars_1m=None, **kwargs):
        ltp = kwargs.get("option_ltp") or 100.0
        levels = bind_option_premium_levels(
            option_ltp=float(ltp),
            lean="CE",
            underlying_spot=24000.0,
            target_pct=0.25,
            stop_pct=0.25,
        )
        return {
            "side": "CE",
            "mix_id": "MIX-CF-TEST",
            "entry": levels["entry"],
            "stop": levels["stop"],
            "target": levels["target"],
            "NO_PROMOTE": True,
        }

    from backtest_engine.cf_paper_registry import CfSignalPlugin, register_plugin

    clear_plugins()
    register_plugin(
        CfSignalPlugin(
            plugin_id="test_only",
            family="test",
            priority=1,
            detect=fake_detect,
        )
    )
    # Prevent default bootstrap from re-adding after clear — mark bootstrapped
    reg._BOOTSTRAPPED = True
    sig = detect_cf_signal("NIFTY", _bars(), option_ltp=100.0)
    assert sig is not None
    assert sig["side"] == "CE"
    assert sig["entry"] == 100.0
    assert abs(float(sig["stop"]) - 75.0) < 1e-6
    assert abs(float(sig["target"]) - 125.0) < 1e-6
    clear_plugins()


def test_structure_signal_empty_without_accept_json(tmp_path, monkeypatch):
    clear_structure_cache()
    monkeypatch.setattr(
        "backtest_engine.cf_structure_paper._recon_glob",
        lambda root: [],
    )
    load_structure_eligible_cells.cache_clear()
    assert load_structure_eligible_cells() == ()
    assert detect_structure_signal("NIFTY", _bars(), option_ltp=100.0) is None


def test_structure_signal_fires_with_stub_cell(monkeypatch):
    clear_structure_cache()
    stub = StructurePaperCell(
        cell="NIFTY|1m|sideways|MIX-CF-MARCO-LIQ-TRAP|SWEEP_RECLAIM|confirm_bars=4",
        mix_id="MIX-CF-MARCO-LIQ-TRAP",
        family="marco_mayne",
        underlying="NIFTY",
        tf_min=1,
        regime="sideways",
        setup="SWEEP_RECLAIM",
        params={"confirm_bars": 4},
        param_key="confirm_bars=4",
        n=40,
        wr_robust=0.55,
    )

    def _fake_load(recon_dir: str = ""):
        return (stub,)

    monkeypatch.setattr(
        "backtest_engine.cf_structure_paper.load_structure_eligible_cells",
        _fake_load,
    )

    # Force lean last bar to CE
    monkeypatch.setattr(
        "backtest_engine.cf_structure_paper.call_lean",
        lambda arm, bars, params: ["SKIP"] * (len(bars) - 1) + ["CE"],
    )
    monkeypatch.setattr(
        "backtest_engine.cf_structure_paper.prep_series",
        lambda bars: (["sideways"] * len(bars), [10.0] * len(bars)),
    )

    sig = detect_structure_signal("NIFTY", _bars(100), option_ltp=80.0)
    assert sig is not None
    assert sig["side"] == "CE"
    assert sig["mix_id"] == "MIX-CF-MARCO-LIQ-TRAP"
    assert sig["entry"] == 80.0
    assert abs(float(sig["stop"]) - 60.0) < 1e-6
    assert abs(float(sig["target"]) - 100.0) < 1e-6
    assert sig["NO_PROMOTE"] is True
