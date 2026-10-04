"""GOOD_EXIT labeller: prominence, no higher later, holes skipped."""

from __future__ import annotations

from exitlab.r3_core import label_window


def test_good_exit_is_peak_with_prominence() -> None:
    # half-spread 0.2 => need 0.3 pts prominence, no higher later in 5
    closes: list[float | None] = [10.0, 10.1, 10.6, 10.4, 10.3, 10.2, 10.1]
    labs = label_window(closes, horizon=5, half_spread=0.2)
    assert labs[2] == "GOOD_EXIT"
    assert labs[0] == "HOLD"


def test_higher_later_is_hold() -> None:
    closes: list[float | None] = [10.0, 10.5, 11.2, 10.4]
    labs = label_window(closes, horizon=5, half_spread=0.2)
    assert labs[1] == "HOLD"  # 11.2 is later
    assert labs[2] == "GOOD_EXIT"


def test_hole_stays_hold() -> None:
    closes: list[float | None] = [10.0, None, 10.8, 10.1]
    labs = label_window(closes, horizon=5, half_spread=0.2)
    assert labs[1] == "HOLD"


def test_small_bump_is_not_good_exit() -> None:
    # half-spread 0.2 => need 0.3 pts; 10.1 - 10.0 is only 0.1
    closes: list[float | None] = [10.0, 10.1, 10.05]
    labs = label_window(closes, horizon=5, half_spread=0.2)
    assert labs[1] == "HOLD"
