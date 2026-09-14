from pathlib import Path

from backtest_engine.run_tv_ep_grid import fixture_bars, synthetic_bars
from backtest_engine.tv_ep.adapters import ADAPTERS, get_adapter
from backtest_engine.tv_ep.catalog import load_catalog, mix_id_ok
from backtest_engine.tv_ep.grid import cell_status, run_tv_ep_grid
from backtest_engine.tv_ep.mapping import map_tv_signal
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
    assert all(e.adapter != "stub" or int(e.ep_id.split("-")[1]) > 25 for e in entries)
    assert "sma_cross" in ADAPTERS
    assert any(e.adapter == "sma_cross" for e in entries)
    assert any(e.adapter == "ag_sell" for e in entries)
    for name in ("ag_sell", "trendmaster_ma", "double_tap", "pmax", "gap_fill"):
        assert name in ADAPTERS
        assert ADAPTERS[name].ported


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
    assert not stubs
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
    desk = tmp_path / "teams" / "06_backtesting" / "docs" / "TV_EP_LEADERBOARD.md"
    assert board.is_file() and md.is_file() and desk.is_file()
    assert "NO_PROMOTE" in md.read_text(encoding="utf-8")
    assert "UNVALIDATED" in desk.read_text(encoding="utf-8")
    kept = {m["mix_id"] for m in report["mix_keep_all"]}
    listing = {e.mix_id for e in load_catalog() if e.mix_id.startswith("MIX-TV-EP-")}
    assert listing <= kept
    assert len([e for e in load_catalog() if int(e.ep_id.split("-")[1]) <= 23]) == 23


def test_listing_adapters_fire_on_fixture() -> None:
    bars = fixture_bars()[("NIFTY", "INDEX")]
    from backtest_engine.tv_ep.ports import PORT_FNS

    for name, params in (
        ("ag_sell", {"MA_length": 40, "ATR_length": 20, "ATR_factor": 2.5}),
        ("trendmaster_ma", {"Short_Term_MA_Length": 9, "Long_Term_MA_Length": 21}),
        ("double_tap", {"Pivot_Length": 20, "Pivot_Tolerance": 15}),
        ("pmax", {"ATR_Length": 10, "ATR_Multiplier": 3.0, "Moving_Average_Length": 10}),
        ("gap_fill", {"invert": 0}),
    ):
        leans = PORT_FNS[name](bars, params)
        assert len(leans) == len(bars)
        assert set(leans) <= {"CE", "PE", "HOLD", "EXIT"}


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


def test_tv_long_short_map_to_buy_ce_pe() -> None:
    assert map_tv_signal("long") == "CE"
    assert map_tv_signal("buy") == "CE"
    assert map_tv_signal("short") == "PE"
    assert map_tv_signal("sell") == "PE"
    assert map_tv_signal("sell", long_only=True) == "EXIT"
    assert map_tv_signal("flat") == "EXIT"
    assert get_adapter("pmax_flip").id == "pmax"
    assert get_adapter("pmax_flip").ported


def test_two_regime_sma_flips_ce_and_pe() -> None:
    bars = synthetic_bars(1500, trend=True)
    sma = get_adapter("sma_cross")
    leans = sma.leans(bars, {"fast": 10, "slow": 50})
    assert "CE" in leans and "PE" in leans
    long_only = get_adapter("sma_step_trail")
    lo = long_only.leans(bars, {"fast": 14, "slow": 28})
    assert "CE" in lo
    assert "EXIT" in lo
    assert "PE" not in lo


def test_keep_all_23_and_ce_pe_on_full_tf_grid(tmp_path: Path) -> None:
    (tmp_path / "teams" / "06_backtesting" / "docs" / "refs").mkdir(parents=True)
    (tmp_path / "teams" / "06_backtesting" / "docs" / "refs" / "NEWS_CALENDAR.yaml").write_text(
        "status: DATA_INSUFFICIENT\ndays: []\n",
        encoding="utf-8",
    )
    report = run_tv_ep_grid(
        None,
        entries=load_catalog(),
        bars_by_key=fixture_bars(),
        timeframes=(1, 3, 5, 15),
        underlyings=("NIFTY", "SENSEX"),
        tapes=("INDEX", "PREMIUM"),
        fetch_live=False,
        write=True,
        root=tmp_path,
    )
    mix_keep = report["mix_keep_all"]
    listing = [m for m in mix_keep if int(m["mix_id"].split("-")[-1]) <= 23]
    assert len(listing) == 23
    assert all(m["keep"] for m in listing)
    tfs = {c["tf"] for c in report["cells"]}
    uls = {c["underlying"] for c in report["cells"]}
    assert tfs == {"1m", "3m", "5m", "15m"}
    assert {"NIFTY", "SENSEX", "BANKNIFTY"} <= uls
    matrix = report["ce_pe_matrix"]
    assert any(s["buy_ce"] and s["tape"] == "INDEX" for s in matrix)
    assert any(s["buy_pe"] and s["tape"] == "INDEX" for s in matrix)
    desk = (tmp_path / "teams" / "06_backtesting" / "docs" / "TV_EP_LEADERBOARD.md").read_text(
        encoding="utf-8"
    )
    assert "MIX-TV-EP-001" in desk and "MIX-TV-EP-023" in desk
    assert "Not a TradingView Strategy Tester clone" in desk

