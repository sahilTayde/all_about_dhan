"""Every exit constant, moved by one small step, must make the backtest gate fail.

Slow (one subprocess per constant, each replaying fixtures until one result moves), so it runs
only with GATE_MUTATION=1 (the `mutation` job in .github/workflows/backtest-gate.yml):

    GATE_MUTATION=1 python -m pytest tools/backtest_gate/tests/test_mutation.py -q
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import mutate  # noqa: E402

pytestmark = pytest.mark.skipif(os.environ.get("GATE_MUTATION") != "1", reason="slow; set GATE_MUTATION=1")


@pytest.fixture(scope="module")
def results() -> dict:
    return mutate.check(list(mutate.EXIT_MUTANTS), jobs=os.cpu_count() or 2)


@pytest.mark.parametrize("name", [n for n in mutate.EXIT_MUTANTS if n not in mutate.UNEXERCISABLE])
def test_gate_catches_exit_constant_step(results: dict, name: str) -> None:
    r = results[name]
    assert "error" not in r, r["error"]
    if name in mutate.NOT_REACHED and not r.get("caught"):
        pytest.xfail(f"not reached by any fixture day yet: {mutate.NOT_REACHED[name]}")
    assert r.get("caught"), f"{name} = {mutate.EXIT_MUTANTS[name]} did not move any fixture"


def test_book_near_threshold_070_to_060_fails_the_gate(results: dict) -> None:
    """The reported miss: EXIT_BOOK_NEAR_FRAC 0.70 -> 0.60 moved real tapes but passed the old gate."""
    assert mutate.EXIT_MUTANTS["EXIT_BOOK_NEAR_FRAC"] == "0.60"
    assert results["EXIT_BOOK_NEAR_FRAC"]["caught"]


@pytest.mark.parametrize("name", list(mutate.UNEXERCISABLE))
def test_documented_unexercisable_constant_still_cannot_move_results(results: dict, name: str) -> None:
    """If one of these starts moving results, drop it from UNEXERCISABLE (and the README list)."""
    r = results[name]
    assert "error" not in r, r["error"]
    assert r["caught"] is None, f"{name} now moves {r['caught']}: remove it from UNEXERCISABLE"
