"""Property tests for contracts: collision resistance."""

from hypothesis import given
from hypothesis import strategies as st

from contracts import order_id


@given(
    account=st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(min_codepoint=32, max_codepoint=126, blacklist_characters="|"),
    ),
    signal=st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(min_codepoint=32, max_codepoint=126, blacklist_characters="|"),
    ),
    leg=st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(min_codepoint=32, max_codepoint=126, blacklist_characters="|"),
    ),
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
