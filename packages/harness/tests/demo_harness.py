"""Assert-based dry-run. Mock broker only. No network. No live Dhan client."""

from __future__ import annotations

from harness.broker import MockOrderBroker, live_ctor_calls
from harness.gates import APPROVAL_ENV, APPROVAL_VALUE
from harness.order import default_intent
from harness.run import run_shadow_test


def main() -> None:
    before = live_ctor_calls()
    env = {
        APPROVAL_ENV: APPROVAL_VALUE,
        "DHAN_CLIENT_ID": "test-client",
        "DHAN_ACCESS_TOKEN": "test-token",
    }
    result = run_shadow_test(
        mode="shadow",
        env=env,
        broker=MockOrderBroker(),
        intent=default_intent(),
    )
    assert result.ok
    assert result.submitted == 1 and result.cancelled == 1 and result.fills == 0
    assert result.states == ("ACKNOWLEDGED->CANCELLED",)
    assert live_ctor_calls() == before
    print("demo_harness OK", result.submitted, result.cancelled)


if __name__ == "__main__":
    main()
