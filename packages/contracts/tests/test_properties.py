"""Property tests for contracts: collision resistance."""

import pytest

hypothesis = pytest.importorskip("hypothesis")

from hypothesis import given
from hypothesis import strategies as st

from contracts import order_id


@given(
    account=st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_characters="|")),
    signal=st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_characters="|")),
    leg=st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_characters="|")),
)
def test_order_id_format(account: str, signal: str, leg: str) -> None:
    """order_id is always 27 chars [a-z0-9] and deterministic."""
    oid = order_id(account, signal, leg)
    assert len(oid) == 27
    assert oid.startswith("aad")
    assert oid.isalnum()
    assert oid.islower()
    # Deterministic
    assert order_id(account, signal, leg) == oid


def test_order_id_collision_1e6() -> None:
    """Generate 10^6 order_ids and assert no collisions."""
    ids = set()
    for i in range(10**6):
        account = f"acc_{i // 10000}"
        signal = f"sg_{i // 100}"
        leg = f"leg_{i % 10}"
        oid = order_id(account, signal, leg)
        ids.add(oid)
    
    assert len(ids) == 10**6, f"Collision detected: {10**6 - len(ids)} duplicates"
