"""Unit checks: model-aware OpenAI chat.completions params for gpt-6-astra."""

from __future__ import annotations

from trading_agents_india.llm import build_chat_completion_params, uses_max_completion_tokens


def test_astra_uses_max_completion_tokens_no_temperature() -> None:
    assert uses_max_completion_tokens("gpt-6-astra") is True
    params = build_chat_completion_params("gpt-6-astra", max_tokens=700)
    assert params == {"model": "gpt-6-astra", "max_completion_tokens": 700}
    assert "temperature" not in params
    assert "max_tokens" not in params


def test_gpt6_family_and_o_series() -> None:
    assert uses_max_completion_tokens("gpt-6") is True
    assert uses_max_completion_tokens("o1-mini") is True
    assert uses_max_completion_tokens("o3") is True
    o1 = build_chat_completion_params("o1", max_tokens=100)
    assert o1["max_completion_tokens"] == 100
    assert "temperature" not in o1


def test_classic_gpt4o_keeps_temperature_and_max_tokens() -> None:
    assert uses_max_completion_tokens("gpt-4o") is False
    assert uses_max_completion_tokens("gpt-5.4") is False
    params = build_chat_completion_params("gpt-4o", max_tokens=500, temperature=0.2)
    assert params == {
        "model": "gpt-4o",
        "temperature": 0.2,
        "max_tokens": 500,
    }
    assert "max_completion_tokens" not in params
