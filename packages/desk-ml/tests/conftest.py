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
