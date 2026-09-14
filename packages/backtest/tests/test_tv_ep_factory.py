from pathlib import Path

from backtest_engine.run_tv_ep_grid import fixture_bars
from backtest_engine.tv_ep.adapters import ADAPTERS, get_adapter
from backtest_engine.tv_ep.catalog import load_catalog, mix_id_ok
from backtest_engine.tv_ep.grid import cell_status, run_tv_ep_grid
from backtest_engine.tv_ep.regime import regime_labels


def test_mix_ids_are_tv_ep_not_strat() -> None:
    assert mix_id_ok("MIX-TV-EP-001")
    assert mix_id_ok("MIX-TV-EP-014")
    assert not mix_id_ok("STRAT-015")
    assert not mix_id_ok("MIX-CHAMP-EMA-ST-5M")
    entries = load_catalog()
    assert entries
    assert all(e.mix_id.startswith("MIX-TV-EP-") for e in entries)
    assert all(e.adapter in ADAPTERS for e in entries)
    assert any(e.adapter == "stub" for e in entries)
    assert "sma_cross" in ADAPTERS
    assert any(e.adapter == "sma_cross" for e in entries)


def test_registry_sma_and_stub() -> None:
    sma = get_adapter("sma_cross")
    stub = get_adapter("stub")
    unknown = get_adapter("not-a-port")
    assert sma.ported and sma.leans is not None
    assert not stub.ported
    assert unknown.id == "stub"


def test_regime_labels_on_fixture() -> None:
    bars = fixture_bars()[("NIFTY", "INDEX")]
    labels = regime_labels(bars)
    assert len(labels) == len(bars)
    assert set(labels) <= {"TREND", "RANGE", "UNKNOWN"}
    assert any(x == "UNKNOWN" for x in labels[:50])


def test_fixture_grid_emits_rows_without_dhan(tmp_path: Path) -> None:
    (tmp_path / "teams" / "06_backtesting" / "docs" / "refs").mkdir(parents=True)
    (tmp_path / "teams" / "06_backtesting" / "docs" / "refs" / "NEWS_CALENDAR.yaml").write_text(
        "status: DATA_INSUFFICIENT\ndays: []\n",
        encoding="utf-8",
    )
    report = run_tv_ep_grid(
        None,
        entries=load_catalog(),
        bars_by_key=fixture_bars(),
        timeframes=(5, 15),
        underlyings=("NIFTY", "SENSEX"),
        tapes=("INDEX", "PREMIUM"),
        fetch_live=False,
        write=True,
        root=tmp_path,
    )
    assert report["promotion"] == "NO_PROMOTE"
    assert report["research_ready_for_programming"] is False
    cells = report["cells"]
    assert cells
    mix_ids = {c["mix_id"] for c in cells}
    assert any(i.startswith("MIX-TV-EP-") for i in mix_ids)
    stubs = [c for c in cells if c["adapter"] == "stub"]
    assert stubs
    assert all(c["status"] == "DATA_INSUFFICIENT" for c in stubs)
    assert all(c["gap"] for c in stubs)
    ported = [c for c in cells if c["adapter"] != "stub"]
    assert any(c["trade_count"] >= 0 for c in ported)
    assert any(c["status"] in ("WATCH", "TESTED_FAIL", "PARK", "DATA_INSUFFICIENT") for c in ported)
    index_ported = [c for c in ported if c["tape"] == "INDEX" and not c.get("gap")]
    if index_ported:
        assert all(c.get("after_cost_points") is None for c in index_ported)
    prem_ported = [c for c in ported if c["tape"] == "PREMIUM" and not c.get("gap")]
    if prem_ported:
        assert all(c.get("cost_model") == "HYPOTHESIS_OPTION_RT_1PCT" for c in prem_ported)
    board = tmp_path / "data" / "recon" / "tv_ep_leaderboard.json"
    md = tmp_path / "data" / "recon" / "tv_ep_leaderboard.md"
    assert board.is_file() and md.is_file()
    assert "NO_PROMOTE" in md.read_text(encoding="utf-8")


def test_cell_status_never_promote() -> None:
    assert cell_status({"gap": "x"}) == "DATA_INSUFFICIENT"
    assert cell_status({"gap": None, "trade_count": 2, "after_cost_points": 9}) == "PARK"
    assert cell_status({"gap": None, "trade_count": 10, "after_cost_points": -1}) == "TESTED_FAIL"
    assert cell_status({"gap": None, "trade_count": 10, "after_cost_points": 1.2}) == "WATCH"
    assert (
        cell_status(
            {
                "gap": None,
                "trade_count": 10,
                "after_cost_points": None,
                "gross_points": 12.0,
            }
        )
        == "WATCH"
    )
