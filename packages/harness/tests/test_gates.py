"""Fail-closed gates: missing approval, missing credentials, live mode refused."""

from __future__ import annotations

import pytest

from harness.gates import (
    APPROVAL_ENV,
    APPROVAL_VALUE,
    EXIT_REFUSED,
    GateDecision,
    HarnessRefused,
    evaluate_gates,
    require_gates,
    require_transport,
)

_CREDS = {"DHAN_CLIENT_ID": "test-client", "DHAN_ACCESS_TOKEN": "test-token"}


def test_refuse_without_approval_flag() -> None:
    decision = evaluate_gates(mode="shadow", env=_CREDS)
    assert decision.ok is False
    assert decision.reason_code == "APPROVAL_MISSING"
    assert "OFF" in decision.message
    with pytest.raises(HarnessRefused) as info:
        require_gates(mode="shadow", env=_CREDS)
    assert info.value.exit_code == EXIT_REFUSED
    assert info.value.reason_code == "APPROVAL_MISSING"
    assert "test-token" not in str(info.value)


def test_refuse_without_credentials() -> None:
    env = {APPROVAL_ENV: APPROVAL_VALUE}
    decision = evaluate_gates(mode="shadow", env=env)
    assert decision.ok is False
    assert decision.reason_code == "CREDENTIALS_MISSING"
    assert not decision.client_id_set
    assert not decision.access_token_set
    with pytest.raises(HarnessRefused) as info:
        require_gates(mode="harness", env=env)
    assert info.value.reason_code == "CREDENTIALS_MISSING"
    assert "test-token" not in str(info.value)


def test_partial_credentials_still_refuse() -> None:
    env = {APPROVAL_ENV: APPROVAL_VALUE, "DHAN_CLIENT_ID": "test-client"}
    decision = evaluate_gates(mode="shadow", env=env)
    assert decision.reason_code == "CREDENTIALS_MISSING"
    assert decision.client_id_set is True
    assert decision.access_token_set is False


@pytest.mark.parametrize("mode", ["live", "limited_live", "dhan", "paper", "replay", "", "bogus"])
def test_refuse_non_shadow_mode(mode: str) -> None:
    env = {APPROVAL_ENV: APPROVAL_VALUE, **_CREDS}
    decision = evaluate_gates(mode=mode, env=env)
    assert decision.ok is False
    assert decision.reason_code == "MODE_REFUSED"


@pytest.mark.parametrize("mode", ["shadow", "harness", "SHADOW", " harness "])
def test_gates_pass_for_allowed_modes(mode: str) -> None:
    env = {APPROVAL_ENV: APPROVAL_VALUE, **_CREDS}
    decision = evaluate_gates(mode=mode, env=env)
    assert decision == GateDecision(True, "OK", "gates passed", mode.strip().lower(), True, True)


def test_wrong_approval_phrase_is_not_enough() -> None:
    env = {APPROVAL_ENV: "I_UNDERSTAND_REAL_MONEY", **_CREDS}
    decision = evaluate_gates(mode="shadow", env=env)
    assert decision.reason_code == "APPROVAL_MISSING"


def test_default_transport_is_off() -> None:
    with pytest.raises(HarnessRefused) as info:
        require_transport("none")
    assert info.value.reason_code == "TRANSPORT_OFF"
    assert require_transport("mock") == "mock"
    assert require_transport("recorded") == "recorded"
    assert require_transport("dhan") == "dhan"
