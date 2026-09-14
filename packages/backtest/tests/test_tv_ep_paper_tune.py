"""PAPER tuner: dual-tape gate, bounded grid, RETUNE_GATE. No orders."""

from pathlib import Path

from backtest_engine.indicators import Bar
from backtest_engine.run_tv_ep_grid import synthetic_bars
from backtest_engine.tv_ep.catalog import CatalogEntry, ParamSpec
from backtest_engine.tv_ep.paper_tune import (
    MAX_TWEAKS_PER_MIX_PER_DAY,
    bounded_param_grid,
    default_buy_leans,
    premium_divergence,
    run_paper_tune,
)


def _triple(n: int = 40, *, ce_follows: bool = True) -> dict[str, list[Bar]]:
    idx = synthetic_bars(n, trend=True)
    ce: list[Bar] = []
    pe: list[Bar] = []
    ce_px = 80.0
    pe_px = 80.0
    for i, b in enumerate(idx):
        prev = idx[i - 1].close if i else b.close
        up = b.close > prev
        if ce_follows:
            ce_px += 1.5 if up else -1.2
            pe_px += -1.2 if up else 1.5
        else:
            ce_px += -1.5 if up else 1.2
            pe_px += 1.5 if up else -1.2
        ce.append(Bar(ts=b.ts, open=ce_px, high=ce_px + 1, low=ce_px - 1, close=ce_px, volume=1))
        pe.append(Bar(ts=b.ts, open=pe_px, high=pe_px + 1, low=pe_px - 1, close=pe_px, volume=1))
    return {"index": idx, "ce": ce, "pe": pe}


def test_divergence_blocks_when_ce_does_not_follow() -> None:
    blocked, why = premium_divergence(
        intended="CE",
        index_prev=24000.0,
        index_now=24020.0,
        ce_prev=80.0,
        ce_now=78.0,
        pe_prev=80.0,
        pe_now=82.0,
    )
    assert blocked is True
    assert "PREMIUM_DIVERGENCE" in why or "did not follow" in why or "HOLD" in why or "PE" in why


def test_ce_follow_allows_ticket() -> None:
    blocked, _ = premium_divergence(
        intended="CE",
        index_prev=24000.0,
        index_now=24020.0,
        ce_prev=80.0,
        ce_now=83.0,
        pe_prev=80.0,
        pe_now=77.0,
    )
    assert blocked is False


def test_bounded_grid_cap() -> None:
    class _A:
        def schema_for(self, _e):
            return {"fast": ParamSpec("int", 10, (8, 10, 13, 21)), "slow": ParamSpec("int", 50, (50,))}

        def param_grid(self, _e):
            return [{"fast": float(x), "slow": 50.0} for x in (8, 10, 13, 21)]

    entry = CatalogEntry("EP-005", "MIX-TV-EP-005", "double_tap")
    grid = bounded_param_grid(_A(), entry, max_tweaks=9)
    assert len(grid) <= MAX_TWEAKS_PER_MIX_PER_DAY


def test_default_buy_momentum() -> None:
    bars = synthetic_bars(20, trend=True)
    leans = default_buy_leans(bars, {"lookback": 1})
    assert set(leans) <= {"CE", "PE", "HOLD"}
    assert any(x in ("CE", "PE") for x in leans)


def test_paper_tune_writes_proposal_not_production(tmp_path: Path) -> None:
    (tmp_path / "teams" / "04_quant" / "docs" / "candidates").mkdir(parents=True)
    report = run_paper_tune(
        root=tmp_path,
        mix_ids=["MIX-DEFAULT-BUY"],
        max_ticks=30,
        max_tweaks=3,
        write=True,
        bars_override=_triple(40, ce_follows=True),
    )
    assert report["promotion"] == "NO_PROMOTE"
    assert report["production_params_written"] is False
    assert report["llm"] is False
    assert report["mixes_ran"] == ["MIX-DEFAULT-BUY"]
    assert report["proposal_paths"]
    text = Path(report["proposal_paths"][0]).read_text(encoding="utf-8")
    assert "BACKTEST_REQUIRED" in text
    assert "keep_current_strategy" in text
    cand = tmp_path / "teams" / "04_quant" / "docs" / "candidates"
    assert list(cand.iterdir()) == []
    board = tmp_path / "data" / "recon" / "tv_ep_leaderboard.json"
    assert board.is_file()
    blob = board.read_text(encoding="utf-8")
    assert "paper_sessions" in blob
    assert "NO_PROMOTE" in blob
    params = list((tmp_path / "data" / "recon").glob("tv_ep_paper_params_*.json"))
    assert params
    assert "mix_default_buy_untouched" in params[0].read_text(encoding="utf-8")


def test_no_tape_stops() -> None:
    report = run_paper_tune(
        root=Path("/tmp/tv-ep-empty-root-tune"),
        mix_ids=["MIX-TV-EP-005"],
        write=False,
        bars_override={"index": [], "ce": [], "pe": []},
    )
    assert report["ok"] is False
    assert report.get("stop") == "no tape" or "tape" in str(report.get("gap") or report.get("stop") or "").lower()
