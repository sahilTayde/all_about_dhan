"""Unit checks: model-aware OpenAI chat.completions params for gpt-6-astra."""

from __future__ import annotations

from trading_agents_india.llm import (
    LlmClient,
    build_chat_completion_params,
    uses_max_completion_tokens,
)


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


def test_transient_and_rate_limit_classifiers() -> None:
    class APIConnectionError(Exception):
        pass

    class RateLimitError(Exception):
        status_code = 429

    assert LlmClient._is_transient_error(APIConnectionError("boom")) is True
    assert LlmClient._is_rate_limit_error(RateLimitError("rate limit")) is True
    assert LlmClient._is_transient_error(RateLimitError("rate limit")) is False


def test_shared_cooldown_roundtrip(tmp_path, monkeypatch) -> None:
    from trading_agents_india import llm as llm_mod

    path = tmp_path / "cooldown.json"
    monkeypatch.setenv("TAI_LLM_COOLDOWN_PATH", str(path))
    llm_mod._RATE_LIMIT_COOLDOWN_UNTIL = 0.0
    llm_mod._rate_limit_strikes = 0
    client = LlmClient("gpt-4o", enabled=False)
    delay = client._mark_rate_limited()
    assert delay >= 29.0
    assert path.is_file()
    # Simulate respawn
    llm_mod._RATE_LIMIT_COOLDOWN_UNTIL = 0.0
    llm_mod._rate_limit_strikes = 0
    llm_mod._sync_from_shared()
    assert llm_mod._RATE_LIMIT_COOLDOWN_UNTIL > 0
    assert client._in_rate_limit_cooldown() is True


def test_clear_rate_limit_preserves_fresher_shared(tmp_path, monkeypatch) -> None:
    """Success in process A must not wipe process B's newer shared cooldown."""
    import time

    from trading_agents_india import llm as llm_mod

    path = tmp_path / "cooldown.json"
    monkeypatch.setenv("TAI_LLM_COOLDOWN_PATH", str(path))
    llm_mod._RATE_LIMIT_COOLDOWN_UNTIL = time.time() + 10.0
    llm_mod._rate_limit_strikes = 1
    llm_mod._persist_shared()
    # Stale local view (as if this process had an older cooldown)
    llm_mod._RATE_LIMIT_COOLDOWN_UNTIL = time.time() + 2.0
    llm_mod._rate_limit_strikes = 1
    client = LlmClient("gpt-4o", enabled=False)
    # Simulate another process writing a fresher mark
    fresher = time.time() + 120.0
    path.write_text(
        __import__("json").dumps(
            {
                "rate_limit_until": fresher,
                "rate_limit_strikes": 3,
                "conn_until": 0.0,
                "conn_strikes": 0,
            }
        ),
        encoding="utf-8",
    )
    client._clear_rate_limit()
    assert llm_mod._RATE_LIMIT_COOLDOWN_UNTIL >= fresher - 1.0
    assert client._in_rate_limit_cooldown() is True


def test_skip_all_short_circuits(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TAI_LLM_COOLDOWN_PATH", str(tmp_path / "cd.json"))
    client = LlmClient("gpt-4o", enabled=False)
    client.skip_all = True
    # Force enabled path without real client
    client.enabled = True
    client._client = object()
    parsed, gaps = client.complete_json(system="x", user="y")
    assert parsed is None
    assert any("skipped" in g.lower() for g in gaps)
