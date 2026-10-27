"""desk-ml test isolation.

Engine code never falls back to this checkout for data: a ``BookEngine`` without a root has no
founder state and fails closed. Tests that need entries pass ``founder_root`` (every index
STARTed in a scratch root). ``_checkout_data_untouched`` fails the run if any test writes under
the checkout's ``data/``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

CHECKOUT = Path(__file__).resolve().parents[3]


def _tree(root: Path) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    if not root.is_dir():
        return out
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            path = Path(dirpath) / name
            try:
                st = path.stat()
            except OSError:
                continue
            out[str(path.relative_to(root))] = (st.st_size, st.st_mtime_ns)
    return out


@pytest.fixture(scope="session", autouse=True)
def _checkout_data_untouched():
    before = _tree(CHECKOUT / "data")
    yield
    after = _tree(CHECKOUT / "data")
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    assert not changed, f"desk-ml tests wrote into the checkout's data/: {changed[:10]}"


@pytest.fixture(scope="session")
def founder_root(tmp_path_factory) -> Path:
    """Scratch data root with NIFTY, BANKNIFTY and SENSEX STARTed since the beginning of time."""
    from desk_ml.founder_session import KNOWN, save_founder_book

    root = tmp_path_factory.mktemp("founder_all")
    save_founder_book(list(KNOWN), root=root, ts=0.0)
    return root


@pytest.fixture
def pre_park_rule_set(monkeypatch):
    """Rule-engine mechanics tests: R01/B3a/R02 live, no config/desk_rules_off.yaml, 20-min timer exits.
    The founder's later desk choices (R02 parked, R01/B3a off 2026-10-12, price-only exits 9bf34a1) are
    covered by test_desk_rules_off.py / test_desk_shadow_only.py, not by these synthetic-tape tests."""
    from desk_ml import research_rules as rr

    monkeypatch.setattr(rr, "LIVE_RULE_IDS", (rr.R01, rr.R01_B3A, rr.R02))
    monkeypatch.setattr(rr, "SHADOW_RULE_IDS", ())
    monkeypatch.setattr(rr, "desk_rules_off", lambda path=None: set())
    monkeypatch.setattr(rr, "PRICE_EXITS", False)
    return rr
