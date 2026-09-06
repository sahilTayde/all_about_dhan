from dhan_client.endpoints import (
    RATE_LIMIT_DATA_PER_SEC,
    RATE_LIMIT_OPTION_CHAIN_SECONDS,
    RATE_LIMIT_QUOTE_PER_SEC,
)
from dhan_client.rate_limit import MinIntervalGate


def test_documented_caps() -> None:
    assert RATE_LIMIT_QUOTE_PER_SEC == 1
    assert RATE_LIMIT_DATA_PER_SEC == 5
    assert RATE_LIMIT_OPTION_CHAIN_SECONDS == 3


def test_gate_zero_first_call() -> None:
    g = MinIntervalGate(0.01)
    slept = g.wait()
    assert slept >= 0.0
