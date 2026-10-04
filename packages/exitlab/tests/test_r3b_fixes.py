"""Round 3b: 1-lot rank, peak thresh, trail ≠ pair, permutation, last3d."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from exitlab.clock import IST, ReplayClock
from exitlab.history import last3d_dir
from exitlab.r3_core import FeatRow
from exitlab.r3_mine import is_clock_spec, permute_labels_within_day
from exitlab.r3_ml import auc, percentile
from exitlab.r3_plans import plan_pattern
from exitlab.r3_run import _expiry_folds, n_exits_changed, pack_trades
from exitlab.types import Entry, OpenState, TradeResult


def _entry(*, lots: int = 1) -> Entry:
    return Entry(
        entry_id="e",
        ts=datetime(2026, 9, 17, 10, 0, tzinfo=IST),
        side="CE",
        strike=23200.0,
        entry_price=100.0,
        lots=lots,
        lot_size=65,
        entry_set="test",
        session="2026-09-17",
        moneyness="ATM",
    )


def _trade(*, entry_id: str, lots: int, net: float, reason: str = "FLATTEN_EOD") -> TradeResult:
    return TradeResult(
        entry_id=entry_id,
        entry_set="legacy" if lots > 1 else "random",
        session="2026-09-17",
        scenario="chop",
        side="CE",
        strike=23200.0,
        lots=lots,
        qty=lots * 65,
        entry_ts="2026-09-17T10:00:00+05:30",
        exit_ts="2026-09-17T15:15:00+05:30",
        entry_price=100.0,
        exit_price=100.0 + net / (lots * 65),
        exit_reason=reason,
        time_in_trade_s=300.0,
        mfe=1.0,
        mae=-1.0,
        mfe_inr=65.0,
        mae_inr=-65.0,
        gross_inr=net,
        charges_inr=0.0,
        net_inr=net,
        plan_id="hold_to_1515",
        data_source="test",
    )


def test_pack_trades_ranks_on_one_lot() -> None:
    mixed = [
        _trade(entry_id="big", lots=25, net=-137_000.0),
        _trade(entry_id="small", lots=1, net=-200.0),
    ]
    packed = pack_trades(mixed, n_variants=3, seed=7)
    assert packed["as_traded_net_inr"] == -137200.0
    assert packed["net_1lot"] == pytest.approx(-137_000.0 / 25 + -200.0)
    assert packed["avg_pts"] is not None
    ones = [_trade(entry_id="a", lots=1, net=-200.0), _trade(entry_id="b", lots=1, net=-5480.0)]
    one_pack = pack_trades(ones, n_variants=3, seed=7)
    assert one_pack["net_1lot"] == one_pack["as_traded_net_inr"]


def test_peak_thresh_is_top_x_percent() -> None:
    scores = [float(i) for i in range(100)]
    thr = percentile(scores, 90.0)
    fired = [s for s in scores if s >= thr]
    assert 8 <= len(fired) <= 12
    assert auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == pytest.approx(1.0)
    assert auc([0, 1, 0, 1], [0.9, 0.1, 0.8, 0.2]) == pytest.approx(0.0)


def test_trail_does_not_exit_on_pattern() -> None:
    checks = [("mom_1", "ge", 0.0)]
    pair = plan_pattern("pat_0_pair", checks)
    trail = plan_pattern("pat_0_trail", checks, trail_give=2.0)
    clock = ReplayClock(datetime(2026, 9, 17, 11, 0, tzinfo=IST))
    ctx = {"mark": 109.0, "r3_feat": {"mom_1": 1.5}}
    st_pair = OpenState(entry=_entry(), remaining_qty=65, seen_high=110.0)
    st_trail = OpenState(entry=_entry(), remaining_qty=65, seen_high=110.0)
    assert pair.decide(st_pair, clock, ctx) == "PATTERN"
    trail_dec = trail.decide(st_trail, clock, ctx)
    assert trail_dec != "PATTERN"
    assert trail_dec == ""
    assert st_trail.trail_stop is not None
    assert st_trail.trail_stop == pytest.approx(108.0)


def test_n_exits_changed_counts_reason_or_time() -> None:
    a = [_trade(entry_id="x", lots=1, net=-10, reason="PATTERN")]
    b = [_trade(entry_id="x", lots=1, net=-12, reason="HARD_STOP")]
    assert n_exits_changed(a, b) == 1
    assert n_exits_changed(a, a) == 0


def test_permute_labels_keeps_features_and_names_clock() -> None:
    rows = [
        FeatRow(
            entry_id="a",
            entry_set="random_hist",
            session="2023-08-01",
            side="CE",
            i=i,
            ts="2023-08-01T10:00:00+05:30",
            label_5="HOLD",
            label_15="GOOD_EXIT" if i % 2 == 0 else "HOLD",
            label_30="HOLD",
            label_eod="HOLD",
            feats={"tod_min": 600.0 + i, "mom_1": float(i)},
        )
        for i in range(8)
    ]
    perm = permute_labels_within_day(rows, seed=3)
    assert [r.feats for r in perm] == [r.feats for r in rows]
    assert {r.label_15 for r in perm} == {r.label_15 for r in rows}
    assert is_clock_spec("tod_min:high+mins_to_1515:low")
    assert not is_clock_spec("tod_min:high+mom_1:high")


def test_expiry_folds_at_least_12() -> None:
    weeks = [f"2024-01-{i:02d}" for i in range(1, 32)] + [f"2024-02-{i:02d}" for i in range(1, 32)]
    weeks += [f"2024-03-{i:02d}" for i in range(1, 32)] + [f"2024-04-{i:02d}" for i in range(1, 32)]
    weeks += [f"2024-05-{i:02d}" for i in range(1, 31)]
    assert len(weeks) >= 154 or len(weeks) >= 120
    folds = _expiry_folds(weeks, 12)
    assert len(folds) >= 12
    train0, test0 = folds[0]
    train1, _test1 = folds[1]
    assert train0.isdisjoint(test0)
    assert train0.issubset(train1)


def test_last3d_dir_and_missing_open(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    import pyarrow as pa
    import pyarrow.parquet as pq

    from exitlab.history import iter_last3d_days

    day = tmp_path / "last3d"
    day.mkdir()
    idx = pa.table(
        {
            "timestamp": [datetime(2023, 8, 1, 10, 0, tzinfo=IST)],
            "open": [19700.0],
            "high": [19710.0],
            "low": [19690.0],
            "close": [19705.0],
            "volume": [1.0],
            "trading_day": ["2023-08-01"],
        }
    )
    opt = pa.table(
        {
            "timestamp": [datetime(2023, 8, 1, 10, 0, tzinfo=IST)],
            "high": [120.0],
            "low": [118.0],
            "close": [119.0],
            "volume": [10.0],
            "open_interest": [100.0],
            "trading_day": ["2023-08-01"],
            "strike": [19700.0],
            "option_type": ["CE"],
            "expiry": ["2023-08-03"],
        }
    )
    pq.write_table(idx, day / "index_last3d.parquet")
    pq.write_table(opt, day / "opt1m_last3d_part1.parquet")
    assert last3d_dir(tmp_path) == day
    got = list(iter_last3d_days(tmp_path))
    assert len(got) == 1
    session, bars, index, expiry = got[0]
    assert session == "2023-08-01"
    assert expiry == "2023-08-03"
    assert bars[0].open == bars[0].close == 119.0
    assert index[0].close == 19705.0
