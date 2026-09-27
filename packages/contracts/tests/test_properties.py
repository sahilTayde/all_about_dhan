"""Property tests for contracts: collision resistance."""

from datetime import datetime, timedelta, timezone

from hypothesis import assume, given
from hypothesis import strategies as st

from contracts import order_id, signal_id

_IST = timezone(timedelta(hours=5, minutes=30))
_ALNUM_TEXT = st.text(
    min_size=1,
    max_size=16,
    alphabet=st.characters(min_codepoint=32, max_codepoint=126, blacklist_characters="|"),
).filter(lambda s: any(c.isalnum() for c in s))


def _signal_args() -> st.SearchStrategy[tuple[str, str, str, datetime, int]]:
    return st.tuples(
        _ALNUM_TEXT,
        _ALNUM_TEXT,
        _ALNUM_TEXT,
        st.datetimes(
            min_value=datetime(2026, 1, 1),
            max_value=datetime(2026, 12, 31, 23, 59, 59),
            timezones=st.just(_IST),
        ),
        st.integers(min_value=0, max_value=10_000),
    )


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


@given(
    a=_signal_args(),
    b=_signal_args(),
)
def test_signal_id_distinct_inputs_distinct_ids(
    a: tuple[str, str, str, datetime, int],
    b: tuple[str, str, str, datetime, int],
) -> None:
    """Accepted distinct (strategy, version, underlying, ts, n) tuples never share an id."""
    assume(a != b)
    assert signal_id(*a) != signal_id(*b)
