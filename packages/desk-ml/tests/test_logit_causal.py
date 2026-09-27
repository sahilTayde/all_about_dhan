"""MIX-ML-LOGIT / LOGIT-XR / GREEKS inputs must be causal: the vote at tick i may only use 3m bars whose bucket has
ended at or before tick i, and must not change when later ticks are removed (live tape end == replay)."""
from __future__ import annotations

import random
from datetime import datetime

import pytest

from desk_ml.paper_scalp import IST, Triple, logit_side_series

pytest.importorskip("backtest_engine.ml_leans")


def _history(seed: int = 3) -> dict[int, float]:
    rng = random.Random(seed)
    closes: dict[int, float] = {}
    px = 22000.0
    for day in (14, 15, 16):
        start = int(datetime(2026, 9, day, 9, 15, tzinfo=IST).timestamp())
        for i in range(125 * 3):  # 1m closes keyed at the minute (chart style)
            px += rng.gauss(0.0, 6.0)
            closes[start + i * 60] = round(px, 2)
    return closes


def _session(seed: int = 5, n: int = 70) -> list[Triple]:
    rng = random.Random(seed)
    ts = int(datetime(2026, 9, 17, 9, 15, 7, tzinfo=IST).timestamp())
    px = 22100.0
    out = []
    for _ in range(n):
        ts += rng.randint(25, 75)  # uneven prints, like the dual tape
        px += rng.gauss(0.0, 7.0)
        out.append(Triple(ts=ts, idx_close=round(px, 2), ce_close=100.0, pe_close=100.0))
    return out


@pytest.mark.parametrize("xr", [False, True])
def test_logit_series_unchanged_when_tape_is_cut(xr: bool) -> None:
    hist, ticks = _history(), _session()
    full, _ = logit_side_series(ticks, index_closes=hist, xr=xr)
    assert any(r.get("side") in {"CE", "PE"} for r in full)
    for k in range(len(ticks)):
        cut, _ = logit_side_series(ticks[: k + 1], index_closes=hist, xr=xr)
        assert [r.get("side") for r in cut] == [r.get("side") for r in full[: k + 1]], k


def test_bar_used_only_after_its_bucket_ends(monkeypatch: pytest.MonkeyPatch) -> None:
    import backtest_engine.ml_leans as ml

    def by_index(bars, *, train_end_ts):  # label every bar by its index so consumption timing is visible
        n = len(bars)
        return ["CE" if i % 2 == 0 else "PE" for i in range(n)], [float(i) for i in range(n)]

    monkeypatch.setattr(ml, "score_ml_logit", by_index)
    hist, ticks = _history(), _session()
    series, _ = logit_side_series(ticks, index_closes=hist, xr=False)
    assert series[-1].get("status") == "OK"
    from desk_ml.paper_scalp import resample_closes_3m

    closes = {k: v for k, v in hist.items() if k < ticks[0].ts}
    for t in ticks:
        closes.setdefault(int(t.ts), float(t.idx_close))
    bars = resample_closes_3m(closes)
    for i, t in enumerate(ticks):
        done = [j for j, b in enumerate(bars) if b.ts >= ticks[0].ts and b.ts - b.ts % 180 + 180 <= t.ts]
        want = ("CE" if done[-1] % 2 == 0 else "PE") if done else None
        assert series[i].get("side") == want, (i, t.ts)
        assert series[i].get("p") == (float(done[-1]) if done else None), (i, t.ts)


def test_same_session_index_closes_are_ignored() -> None:
    hist, ticks = _history(), _session()
    base, _ = logit_side_series(ticks, index_closes=hist, xr=False)
    poisoned = dict(hist)
    for t in ticks:  # a chart fetch that already holds today's minutes (keyed at the minute OPEN)
        poisoned[int(t.ts) - int(t.ts) % 60] = float(t.idx_close) + 500.0
    got, _ = logit_side_series(ticks, index_closes=poisoned, xr=False)
    assert [r.get("side") for r in got] == [r.get("side") for r in base]


def test_chart_minute_open_before_first_print_is_not_history() -> None:
    hist, ticks = _history(), _session()
    first = int(ticks[0].ts)
    assert first % 60
    _, base = logit_side_series(ticks, index_closes=hist, xr=False)
    _, got = logit_side_series(ticks, index_closes={**hist, first - first % 60: 1.0}, xr=False)
    assert got["n_index_1m"] == base["n_index_1m"]
