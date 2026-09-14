from backtest_engine.flawless_victory import (
    FlawlessParams,
    bollinger_tv,
    flawless_signals,
    mfi,
)
from backtest_engine.indicators import Bar


def _bars(n: int = 80) -> list[Bar]:
    out = []
    px = 100.0
    for i in range(n):
        # gentle wave + volume
        px = 100 + (i % 17) - 8
        out.append(
            Bar(
                ts=1_700_000_000 + i * 60,
                open=px,
                high=px + 1,
                low=px - 1,
                close=px,
                volume=100 + (i % 5) * 10,
            )
        )
    return out


def test_mfi_and_bb_finite() -> None:
    bars = _bars()
    mf = mfi(bars, 14)
    assert any(x is not None for x in mf)
    c = [b.close for b in bars]
    lo, mid, hi = bollinger_tv(c, 20, 1.0)
    assert mid[19] is not None
    assert lo[19] < mid[19] < hi[19]


def test_v1_signals_run() -> None:
    bars = _bars(100)
    e, x = flawless_signals(bars, FlawlessParams("v1"))
    assert len(e) == len(bars) == len(x)
