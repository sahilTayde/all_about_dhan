from backtest_engine.indicators import Bar, wma
from backtest_engine.itm_scalp import (
    ItmScalpParams,
    itm_scalp_signals,
    simulate_itm_scalp_long,
    summarize_lot_pnl,
)


def test_wma_weights() -> None:
    out = wma([1.0, 2.0, 3.0, 4.0], 3)
    assert out[0] is None and out[1] is None
    assert abs(out[2] - 14.0 / 6.0) < 1e-9


def _synth_up_then_down(n: int = 80) -> list[Bar]:
    bars: list[Bar] = []
    base_ts = 1_725_000_000
    px = 50.0
    for i in range(n):
        if i < 40:
            px += 1.5
        else:
            px -= 2.0
        bars.append(
            Bar(
                ts=base_ts + i * 60,
                open=px - 0.2,
                high=px + 0.5,
                low=px - 0.5,
                close=px,
                volume=1000.0 + i,
            )
        )
    return bars


def test_bullish_state_enters_more_than_cross_event() -> None:
    bars = _synth_up_then_down()
    loose = ItmScalpParams(rsi_entry_th=50.0, rsi_exit_th=45.0, ma_mode="bullish_state")
    strict = ItmScalpParams(rsi_entry_th=50.0, rsi_exit_th=45.0, ma_mode="cross_event")
    e1, _ = itm_scalp_signals(bars, loose)
    e2, _ = itm_scalp_signals(bars, strict)
    assert sum(e1) >= sum(e2)


def test_itm_scalp_sl_tp_and_lot_pnl() -> None:
    bars = _synth_up_then_down()
    params = ItmScalpParams(
        rsi_entry_th=50.0,
        rsi_exit_th=45.0,
        ma_mode="bullish_state",
        fill_mode="signal_close",
        stop_loss_frac=0.15,
        target_frac=0.30,
    )
    trades = simulate_itm_scalp_long(bars, side="PE", params=params)
    summary = summarize_lot_pnl(trades, lot_size=65, lots=1)
    assert summary["lot_size"] == 65
    if trades:
        assert abs(summary["gross_pnl_inr"] - summary["gross_points"] * 65) < 1e-6
