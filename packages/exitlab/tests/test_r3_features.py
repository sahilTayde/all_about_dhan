"""Features use only minutes before i. Labels are not features."""

from __future__ import annotations

from datetime import datetime

from exitlab.clock import IST
from exitlab.r3_core import Minute, features_before, shift_minutes
from exitlab.types import Entry


def _ts(h: int, m: int) -> datetime:
    return datetime(2026, 9, 17, h, m, tzinfo=IST)


def _mins(n: int = 20) -> list[Minute]:
    out = []
    px = 100.0
    idx = 23300.0
    for i in range(n):
        px += 0.2 if i % 3 else -0.1
        idx += 1.0
        t = _ts(10, i)
        out.append(Minute(ts=t, available_ts=t, ltp=px, index=idx, spread=0.4, hole=False))
    return out


def _entry() -> Entry:
    return Entry(
        entry_id="e",
        ts=_ts(10, 0),
        side="CE",
        strike=23200.0,
        entry_price=100.0,
        lots=1,
        lot_size=65,
        entry_set="test",
        session="2026-09-17",
        moneyness="ATM",
    )


def test_features_ignore_future_shuffle() -> None:
    mins = _mins(24)
    cut = 8
    a = features_before(
        mins,
        cut,
        entry=_entry(),
        day_index=[m.index or 0 for m in mins[:cut]],
        regime="chop",
        expiry=False,
    )
    b = features_before(
        shift_minutes(mins, seed=3),
        cut,
        entry=_entry(),
        day_index=[m.index or 0 for m in mins[:cut]],
        regime="chop",
        expiry=False,
    )
    assert a
    assert a == b


def test_label_keys_are_not_features() -> None:
    feat = features_before(
        _mins(), 6, entry=_entry(), day_index=[23300.0] * 6, regime="chop", expiry=False
    )
    for banned in ("label_5", "label_15", "GOOD_EXIT", "HOLD"):
        assert banned not in feat
