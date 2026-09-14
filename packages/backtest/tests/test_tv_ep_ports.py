from backtest_engine.indicators import Bar
from backtest_engine.run_tv_ep_grid import fixture_bars
from backtest_engine.tv_ep.adapters import ADAPTERS, get_adapter
from backtest_engine.tv_ep.catalog import load_catalog
from backtest_engine.tv_ep.ports import (
    bot3c_ma,
    csv_replay,
    ema_trail,
    gap_fill,
    grid_like,
    grover_llorens,
    keltner_stop,
    pmax,
    sma_sltp_money,
    stoch_kd,
    timed_sma,
    trendmaster_ma,
)


def _bars() -> list[Bar]:
    return fixture_bars()[("NIFTY", "INDEX")]


def _assert_lean_alphabet(leans: list[str]) -> None:
    assert leans
    assert set(leans) <= {"CE", "PE", "HOLD"}


def test_catalog_listing_adapters_are_named_ports() -> None:
    entries = load_catalog()
    listing = [e for e in entries if 1 <= int(e.ep_id.split("-")[1]) <= 23]
    assert len(listing) == 23
    assert all(e.adapter != "stub" for e in listing)
    assert all(e.adapter in ADAPTERS for e in listing)
    assert all(get_adapter(e.adapter).ported for e in listing)
    assert all(e.mix_id.startswith("MIX-TV-EP-") for e in listing)
    assert "sma_cross" in ADAPTERS
    stub = get_adapter("stub")
    assert not stub.ported


def test_several_adapters_long_short_flat() -> None:
    bars = _bars()
    cases = [
        trendmaster_ma(bars, {"Short_Term_MA_Length": 9, "Long_Term_MA_Length": 21}),
        ema_trail(bars, {"Fast_len": 20, "Slow_len": 50}),
        bot3c_ma(bars, {"MA_Length_1": 21, "MA_Length_2": 50}),
        stoch_kd(bars, {"K": 13, "D": 3, "Smooth": 4}),
        keltner_stop(bars, {"length": 20, "Multiplier": 1.0, "ATR_Length": 10}),
        sma_sltp_money(bars, {"fast": 14, "slow": 28}),
        pmax(bars, {"ATR_Length": 10, "ATR_Multiplier": 3.0, "Moving_Average_Length": 10}),
        grid_like(bars, {"point": 2.0}),
        timed_sma(bars, {"FastMA_Length": 14, "SlowMA_Length": 28}),
        grover_llorens(bars, {"length": 20, "mult": 14.0}),
    ]
    saw_ce = saw_pe = saw_hold = False
    for leans in cases:
        _assert_lean_alphabet(leans)
        assert len(leans) == len(bars)
        saw_ce = saw_ce or ("CE" in leans)
        saw_pe = saw_pe or ("PE" in leans)
        saw_hold = saw_hold or ("HOLD" in leans)
    assert saw_ce and saw_pe and saw_hold


def test_csv_replay_is_flat_without_hook() -> None:
    bars = _bars()
    flat = csv_replay(bars, {})
    assert set(flat) == {"HOLD"}
    hooked = csv_replay(bars, {"csv_long": 1})
    assert "CE" in hooked


def test_gap_fill_detects_session_jump() -> None:
    from datetime import datetime, timedelta, timezone

    ist = timezone(timedelta(hours=5, minutes=30))
    d0 = datetime(2026, 8, 3, 15, 29, tzinfo=ist)
    d1 = datetime(2026, 8, 4, 9, 15, tzinfo=ist)
    bars = [
        Bar(ts=int(d0.timestamp()), open=100, high=101, low=99, close=100, volume=1),
        Bar(ts=int(d1.timestamp()), open=110, high=111, low=109, close=110, volume=1),
    ]
    leans = gap_fill(bars, {"invert": 0})
    assert leans[1] == "PE"  # up-gap faded
    inv = gap_fill(bars, {"invert": 1})
    assert inv[1] == "CE"
